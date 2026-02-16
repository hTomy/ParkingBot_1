import weaviate
from weaviate.classes.config import Configure

if __name__ == '__main__':

    with weaviate.connect_to_local() as client:
        client.collections.create(
            name="MovieOpen",
            vector_config=Configure.Vectors.text2vec_openai(),  # Configure the Weaviate Embeddings vectorizer
        )


        data_objects = [
            {"title": "The Matrix",
             "description": "A computer hacker learns about the true nature of reality and his role in the war against its controllers.",
             "genre": "Science Fiction"},
            {"title": "Spirited Away",
             "description": "A young girl becomes trapped in a mysterious world of spirits and must find a way to save her parents and return home.",
             "genre": "Animation"},
            {"title": "The Lord of the Rings: The Fellowship of the Ring",
             "description": "A meek Hobbit and his companions set out on a perilous journey to destroy a powerful ring and save Middle-earth.",
             "genre": "Fantasy"},
        ]

        movies = client.collections.use("MovieOpen")
        with movies.batch.fixed_size(batch_size=200) as batch:
            for obj in data_objects:
                batch.add_object(properties=obj)

        print(f"Imported & vectorized {len(movies)} objects into the Movie collection")