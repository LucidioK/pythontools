import subprocess
import sys

try:
    import pandas as pd
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pandas"])
    import pandas as pd

try:
    from azure.identity              import ChainedTokenCredential, DefaultAzureCredential
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "azure-identity"])
    from azure.identity              import ChainedTokenCredential, DefaultAzureCredential

try:
    from azure.kusto.data            import KustoClient, KustoConnectionStringBuilder
    from azure.kusto.data.exceptions import KustoThrottlingError
    from azure.kusto.data.response   import KustoResponseDataSet
except ImportError:
    # this also brings azure.kusto.data.exceptions and azure.kusto.data.response
    subprocess.check_call([sys.executable, "-m", "pip", "install", "azure-kusto-data"])
    from azure.kusto.data            import KustoClient, KustoConnectionStringBuilder
    from azure.kusto.data.exceptions import KustoThrottlingError
    from azure.kusto.data.response   import KustoResponseDataSet

try:
    from retry import retry
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "retry"])

# ANSI color codes for terminal output
GREEN    = "\033[92m"
CYAN     = "\033[96m"
YELLOW   = "\033[0;33m"
RED      = "\033[0;31m"
NO_COLOR = "\033[0m"

class KustoUtilsError(Exception):
    pass

class KustoUtils:
    """
    A utility class for interacting with Azure Kusto databases.

    This class provides utility functions for executing Kusto queries and retrieving database
    schema.

    Most importantly, all results are returned as pandas DataFrames for easy data manipulation.

    Attributes:
        cluster_url (str): The URL of the Azure Kusto cluster.
        database_name (str): The name of the Azure Kusto database.
        client (KustoClient): An instance of KustoClient for executing queries.
        version (KustoResponseDataSet): The version information of the Azure Kusto database.
    """

    def __init__(self, cluster_url: str, database_name: str):
        """
        Initialize a KustoUtils instance.

        Parameters:
            cluster_url (str): The URL of the Azure Kusto cluster.
            database_name (str): The name of the Azure Kusto database.
        """
        self.cluster_url: str = cluster_url
        self.database_name: str = database_name
        self.credential: ChainedTokenCredential = KustoUtils.connect_to_azure(cluster_url)

    def get_kusto_database_schema(self) -> pd.DataFrame:
        """
        Retrieves the schema of the specified Kusto database.

        Returns:
            A pandas DataFrame containing the schema of the database.
        """
        query = f".show database schema | extend ClusterUrl='{self.cluster_url}'"
        with self._get_kusto_client() as client:
            return self._get_kusto_resultset(
                KustoUtils.execute_query(client=client, database=self.database_name, query=query)
            )

    def query(self, query: str) -> pd.DataFrame:
        """
        Executes a Kusto query on the specified database and returns the result as a pandas
        DataFrame.

        Parameters:
            query (str): The Kusto query to be executed.

        Returns:
            pd.DataFrame: A pandas DataFrame containing the result of the Kusto query.
        """
        query = query.replace(r"\|", r"|")
        try:
            with self._get_kusto_client() as client:
                return self._get_kusto_resultset(
                    KustoUtils.execute_query(
                        client=client, database=self.database_name, query=query
                    )
                )
        except Exception as e:
            raise KustoUtilsError(
                f"Error executing query: {e}\n\n"
                f"Cluster URL: {self.cluster_url}\n"
                f"Database Name: {self.database_name}\n"
                f"Query: \n{query}"
            )

    def _get_kusto_resultset(self, kusto_response: KustoResponseDataSet) -> pd.DataFrame:
        """
        Converts the Kusto response dataset to a pandas DataFrame.

        Parameters:
            kusto_response (KustoResponseDataSet): The Kusto response dataset.

        Returns:
            pd.DataFrame: A pandas DataFrame containing the result of the Kusto query.
        """
        return pd.DataFrame.from_records(
            [row.to_dict() for row in kusto_response.primary_results[0]]
        )

    def _get_kusto_client(self) -> KustoClient:
        """
        Creates and returns a KustoClient instance using the provided Azure credentials.

        This method checks if the Azure credentials are available and raises
        an exception if they are not.
        It then creates a KustoClient instance using the KustoConnectionStringBuilder with
        the provided cluster URL and Azure credentials.

        Parameters:
        self (KustoUtils): The instance of KustoUtils.

        Returns:
        KustoClient: An instance of KustoClient for executing queries.

        Raises:
        Exception: If the Azure credentials are not available.
        """
        if self.credential is None:
            raise Exception(
                "Access token is empty, please create this object "
                "again with proper Azure connection."
            )
        return KustoClient(
            KustoConnectionStringBuilder.with_azure_token_credential(
                connection_string=self.cluster_url, credential=self.credential
            )
        )

    @retry(KustoThrottlingError, tries=8, delay=20, backoff=10, logger=None)
    @staticmethod
    def execute_query(client: KustoClient, query: str, database) -> KustoResponseDataSet:
        """
        Executes the provided query on the specified database and returns the result as a
        KustoResponseDataSet.

        Parameters:
            query (str): The Kusto query to be executed.

        Returns:
            KustoResponseDataSet: The result of the Kusto query.
        """
        return client.execute(database=database, query=query)

    @staticmethod
    def connect_to_azure(token_request_context: str) -> ChainedTokenCredential:
        """
        Connects to Azure using the provided token_request_context and returns a
        ChainedTokenCredential instance.

        This function initializes a DefaultAzureCredential instance and attempts to create a
        KustoClient instance using the provided token_request_context and the
        DefaultAzureCredential.
        If successful, it returns the initialized credential.
        If an exception occurs, it returns None.

        Parameters:
        token_request_context (str): The connection string for the Azure Kusto cluster.

        Returns:
        ChainedTokenCredential: An instance of ChainedTokenCredential if the connection is
        successful. None if an exception occurs.
        """
        token_request_context = token_request_context.replace(r"https:\\\\", "https://")
        credential = DefaultAzureCredential()
        try:
            with KustoClient(
                KustoConnectionStringBuilder.with_azure_token_credential(
                    connection_string=token_request_context, credential=credential
                )
            ) as client:
                _ = KustoUtils.execute_query(
                    client=client, database="default", query=".show version"
                )
        except Exception as e:
            raise KustoUtilsError(
                f"Failed to connect to Azure cluster {token_request_context}."
                " Please make sure you are connected to Azure "
                "(either run az login or Connect-AzAccount -UseDeviceAuthentication) "
                f"with exception {e}."
            )
        return credential


def kusto_query_to_json(cluster_url: str, database_name: str, query: str) -> None:
    """
    Executes a Kusto query on the specified database and returns the result as a pandas DataFrame.

    Parameters:
        cluster_url (str): The URL of the Azure Kusto cluster.
        database_name (str): The name of the Azure Kusto database.
        query (str): The Kusto query to be executed.

    Returns:
        pd.DataFrame: A pandas DataFrame containing the result of the Kusto query.
    """
    print(KustoUtils(cluster_url, database_name).query(query).to_json(date_format="iso", indent=2))


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="A tool for executing Kusto queries and retrieving database schema."
    )
    parser.add_argument(
        "--cluster-url", 
        "-c", 
        required=True, 
        type=str, 
        help="The URL of the Azure Kusto cluster."
    )
    parser.add_argument(
        "--database-name",
        "-d",
        required=True,
        type=str,
        help="The name of the Azure Kusto database.",
    )
    parser.add_argument(
        "--query",
        "-q",
        required=True,
        type=str,
        help="The Kusto query to be executed, can be a query string\n"
        "or the name of a file with extension .kql.",
    )
    parser.add_argument(
        "--output-format",
        "-o",
        required=False,
        type=str,
        help="Output format, must be JSON or CSV.",
        default="JSON",
        choices=["JSON", "CSV"],
    )
    parser.add_argument(
        "--to-file",
        "-t",
        required=False,
        type=str,
        help="File name to output, default is None.",
        default="",
    )
    args = parser.parse_args()
    query = args.query
    if query.endswith(".kql"):
        with open(query) as file:
            query = file.read()
    result = KustoUtils(args.cluster_url, args.database_name).query(query)
    if args.to_file:
        if args.output_format == "JSON":
            result.to_json(args.to_file, orient="records", date_format="iso", indent=2)
        elif args.output_format == "CSV":
            result.to_csv(args.to_file, index=False)
    elif args.output_format == "JSON":
        print(result.to_json(date_format="iso", indent=2))
    elif args.output_format == "CSV":
        print(result.to_csv(index=False))
