import oci
from oci.signer import Signer
from src.common.config import *

# src/common/connection.py
#from __future__ import annotations
import os
import json
from typing import Any, Dict, List, Optional

import oci
from oci.signer import Signer
from oci.resource_search.models import StructuredSearchDetails


class dbtools_connection:
    """
    Centralized OCI/DB Tools wiring:
      - Loads ~/.oci/config (profile from $OCI_PROFILE, default DEFAULT)
      - Builds signed OCI clients
      - Exposes tenancy_id, config, signer, ords_endpoint
      - Provides helpers: structured search, resolve connection by display name,
        and execute SQL via DB Tools ORDS
    Env required:
      - DBTOOLS_ORDS_ENDPOINT (e.g. https://dbtools.us-ashburn-1.oci.oraclecloud.com)
    Optional:
      - OCI_PROFILE
      - OCI_VECTOR_MODEL (default: OCI__TEXT_EMBEDDING__MINI)
      - OCI_VECTOR_DIM (default: 768)
    """

    def __init__(self) -> None:
        profile = os.getenv("OCI_PROFILE", "DEFAULT")
        self.config = oci.config.from_file(
            file_location=os.path.expanduser("~/.oci/config"),
            profile_name=profile,
        )

        self.tenancy_id = self.config["tenancy"]
        self.auth_signer: Signer = Signer(
            tenancy=self.config["tenancy"],
            user=self.config["user"],
            fingerprint=self.config["fingerprint"],
            private_key_file_location=self.config["key_file"],
            pass_phrase=self.config.get("pass_phrase"),
        )

        # ords = os.environ.get("DBTOOLS_ORDS_ENDPOINT")
        # if not ords:
        #     raise RuntimeError(
        #         "Set DBTOOLS_ORDS_ENDPOINT env var (e.g., https://dbtools.<region>.oci.oraclecloud.com)"
        #     )
        # self.ords_endpoint = ords.rstrip("/")
   
        # Clients
        self.identity_client = oci.identity.IdentityClient(self.config, signer=self.auth_signer)
        self.search_client = oci.resource_search.ResourceSearchClient(self.config, signer=self.auth_signer)
        self.database_client = oci.database.DatabaseClient(self.config, signer=self.auth_signer)
        self.dbtools_client = oci.database_tools.DatabaseToolsClient(self.config, signer=self.auth_signer)

        self.ords_endpoint = self.dbtools_client.base_client._endpoint.replace("https://", "https://sql.")

        # Vector config (used by report/rag helpers)
        self.MODEL_NAME = os.getenv("OCI_VECTOR_MODEL", "OCI__TEXT_EMBEDDING__MINI")
        self.MODEL_EMBEDDING_DIMENSION = int(os.getenv("OCI_VECTOR_DIM", "768"))

    # ---------- Static wrappers to support class-style calls in tests ----------

    @staticmethod
    def execute_sql_by_connection_id(conn: "dbtools_connection",
                                     connection_id: str,
                                     sql_script: str,
                                     binds: Optional[List[dict]] = None) -> str:
        """Static wrapper so tests can call:
           dbtools_connection.execute_sql_by_connection_id(conn, ...)."""
        return conn._execute_sql_by_connection_id_impl(connection_id, sql_script, binds)

    @staticmethod
    def get_minimal_connection_by_name(conn: "dbtools_connection",
                                       display_name: str) -> Optional[Dict[str, Any]]:
        """Static wrapper so tests can call:
           dbtools_connection.get_minimal_connection_by_name(conn, ...)."""
        return conn._get_minimal_connection_by_name_impl(display_name)

    @staticmethod
    def resource_search(conn: "dbtools_connection", query: str) -> Any:
        """Static wrapper for resource search if tests call class method."""
        return conn._resource_search_impl(query)

    # ------------------------- Instance implementations ------------------------

    def _resource_search_impl(self, query: str) -> Any:
        details = StructuredSearchDetails(
            query=query,
            type="Structured",
            matching_context_type="NONE",
        )
        return self.search_client.search_resources(
            search_details=details, tenant_id=self.config["tenancy"]
        ).data

    def _get_minimal_connection_by_name_impl(self, display_name: str) -> Optional[Dict[str, Any]]:
        details = StructuredSearchDetails(
            query=("query databasetoolsconnection resources return allAdditionalFields "
                   f"where displayName =~ '{display_name}'"),
            type="Structured",
            matching_context_type="NONE",
        )
        try:
            resp = self.search_client.search_resources(
                search_details=details, tenant_id=self.config["tenancy"]
            ).data
            if not getattr(resp, "items", None):
                return None
            item = resp.items[0]
            info = {
                "id": item.identifier,
                "display_name": item.display_name,
                "time_created": item.time_created,
                "compartment_id": item.compartment_id,
                "lifecycle_state": item.lifecycle_state,
            }
            additional = getattr(item, "additional_details", None)
            if isinstance(additional, dict):
                info["type"] = additional.get("type")
                info["connection_string"] = additional.get("connectionString")
            return info
        except Exception:
            return None

    def _execute_sql_by_connection_id_impl(self,
                                           connection_id: str,
                                           sql_script: str,
                                           binds: Optional[List[dict]] = None) -> str:
        import requests
        try:
            url = f"{self.ords_endpoint}/ords/{connection_id}/_/sql"
            payload = {"statementText": sql_script}
            if binds:
                payload["binds"] = binds

            resp = requests.post(
                url,
                json=payload,
                auth=self.auth_signer,  # OCI Request Signer
                headers={"Content-Type": "application/json"},
            )
            try:
                return json.dumps(resp.json(), indent=2)
            except Exception:
                return json.dumps({"status_code": resp.status_code, "text": resp.text}, indent=2)
        except Exception as e:
            # IMPORTANT: return a JSON error (your test named *_exception likely asserts this)
            return json.dumps(
                {"error": f"Error executing SQL: {str(e)}", "sql_script": sql_script, "binds": binds},
                indent=2,
            )


# profile_name = os.getenv("OCI_PROFILE", "DEFAULT")

# config = oci.config.from_file(profile_name=profile_name)

# identity_client = oci.identity.IdentityClient(config)
# search_client = oci.resource_search.ResourceSearchClient(config)
# database_client = oci.database.DatabaseClient(config)
# dbtools_client = oci.database_tools.DatabaseToolsClient(config)
# vault_client = oci.vault.VaultsClient(config)
# secrets_client = oci.secrets.SecretsClient(config)
# ords_endpoint = dbtools_client.base_client._endpoint.replace("https://", "https://sql.")

# auth_signer = Signer(
#     tenancy=config['tenancy'],
#     user=config['user'],
#     fingerprint=config['fingerprint'],
#     private_key_file_location=config['key_file'],
#     pass_phrase=config['pass_phrase']
# )
# tenancy_id = os.getenv("TENANCY_ID_OVERRIDE", config['tenancy'])

if __name__ == '__main__':
    conn = dbtools_connection()
    identity_client = conn.identity_client
    print(identity_client)