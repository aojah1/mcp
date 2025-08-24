## DEPLOYMENT OF A LOCAL ORACLE DB

# 1) Is the VM even running?
podman machine list

# 2) Start (or restart) it
podman machine stop || true
podman machine start

# 3) Use Podman’s managed connection instead of a hardcoded port
podman system connection ls
podman system connection default  podman-machine-default-root  # pick the right name from the list

# 4) Test
podman info
podman ps

# 5) (Official Oracle Database Free container image.) 
podman pull container-registry.oracle.com/database/free:latest

# 6)
podman volume create oradata

# 7) 
podman run -d --name oracle-free \
  -p 1521:1521 \
  -v oradata:/opt/oracle/oradata \
  -e ORACLE_PWD=Oracle_123 \
  container-registry.oracle.com/database/free:latest

# 8) 
podman logs -f oracle-free   # watch startup

# 9) Connect
#### Default services: FREE (CDB) and FREEPDB1 (PDB). Example with SQL*Plus/SQLcl:

sqlplus sys/Oracle_123@localhost:1521/FREEPDB1 as sysdba

# or inside the container
podman exec -it oracle-free bash
sqlplus sys/Oracle_123@localhost:1521/FREEPDB1 as sysdba

# 10 ) Final step to enable MCP 
conn -save cline_mcp -savepwd sys/Oracle_123@localhost:1521/FREEPDB1 as sysdba
