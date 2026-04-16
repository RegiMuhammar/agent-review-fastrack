import sys
from app.graph.builder import review_pipeline

try:
    png_data = review_pipeline.get_graph().draw_mermaid_png()
    with open("pipeline.png", "wb") as f:
        f.write(png_data)
    print("Success: Generated pipeline.png")
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)
