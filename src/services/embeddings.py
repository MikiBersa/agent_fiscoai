from openai import AzureOpenAI


class EmbeddingAzure:
    def __init__(self):
        endpoint = "https://llm-taxai.openai.azure.com/"
        self.model_name = "text-embedding-3-small"
        self.deployment = "text-embedding-3-small"

        self.api_version = "2024-02-01"

        self.client = AzureOpenAI(
            api_version="2024-12-01-preview",
            azure_endpoint=endpoint,
            api_key="ChSYcqLmTJdqnEUtRQZ6JfkjZYCO9cfPzXlqcxdp4SLYnIydZGGXJQQJ99CCACYeBjFXJ3w3AAABACOGb6CU",
        )

    def calculate_emebddings(self, texts: list[str]):
        response = self.client.embeddings.create(
            input=texts,
            model=self.deployment,
        )

        all_emebeddings = []

        for item in response.data:
            all_emebeddings.append(item.embedding)

        return all_emebeddings
