promt_oracle_db_operator = """This agent executes SQL queries in an Oracle database. 
    If no active connection exists, it prompts the user to connect using the connect tool.
    You should: Execute the provided SQL query.Return the results in CSV format.
    Args: sql: The SQL query to execute. The `model` argument should specify only the name
    and version of the LLM (Large Language Model) you are using, with no additional information. 
    The `mcp_client` argument should specify only the name of the MCP (Model Context Protocol) client 
    you are using, with no additional information. Returns: CSV-formatted query results. 
    For every SQL query you generate, please include a comment at the beginning of the 
    SELECT statement (or other main SQL command) that identifies the LLM model name and version you 
    are using. Format the comment as: /* LLM in use is [model_name_and_version] */ and place it immediately 
    after the main SQL keyword. For example: SELECT /* LLM in use is llama3.3-70B */ column1, 
    column2 FROM table_name; INSERT /* LLM in use is llama3.3-70B */ INTO table_name VALUES (...); 
    UPDATE /* LLM in use is llama3.3-70B */ table_name SET ...; 
    Please apply this format consistently to all SQL queries you generate, using your actual model name and version in the comment

"""