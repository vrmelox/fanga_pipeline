import os
from dotenv import load_dotenv
from pipeline import Pipeline

load_dotenv()

if __name__ == "__main__":
    pipeline = Pipeline(
        input_folder="fanga_inbox",
        output_folder="fanga_organised",
        api_key=os.getenv("API_KEY"),
        threshold=0.70
    )
    print(os.getenv("API_KEY"))
    pipeline.run()