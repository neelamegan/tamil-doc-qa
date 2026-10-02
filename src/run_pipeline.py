# src/run_pipeline.py
import ocr, normalize, chunk, index

if __name__ == "__main__":
    ocr.run()
    normalize.run()
    chunk.run()
    index.run()
    print("pipeline complete")