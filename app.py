"""
app.py — entry point.
Boots the ReportService and launches Gradio.
"""
from core.report_service import ReportService
from ui.gradio_app import create_gradio_ui

if __name__ == "__main__":
    print("Starting Competitive Intelligence Agent...")

    report_service = ReportService()
    demo = create_gradio_ui(report_service)

    print("Launching UI at http://127.0.0.1:7860")
    demo.launch()