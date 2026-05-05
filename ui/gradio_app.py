"""
Gradio UI — knows nothing about LangGraph or the agent internals.
"""
import gradio as gr
from core.report_service import ReportService


def create_gradio_ui(report_service: ReportService):

    def generate_handler(company_name: str, progress=gr.Progress()):
        if not company_name or not company_name.strip():
            return "Please enter a company name.", ""

        progress(0.0, desc="Starting...")

        report = report_service.generate_report(
            company_name,
            progress_callback=lambda p, desc: progress(p, desc=desc)
        )

        return report, report

    def clear_handler():
        return "", "", ""

    with gr.Blocks(title="Competitive Intelligence Agent") as demo:

        gr.Markdown("# Competitive Intelligence Agent")
        gr.Markdown(
            "Enter a company name to generate a structured intelligence briefing. "
            "The agent will search the web, gather recent information, and produce a report."
        )

        with gr.Row():
            with gr.Column(scale=3):
                company_input = gr.Textbox(
                    placeholder="e.g. Salesforce, Stripe, Anthropic...",
                    label="Company Name",
                    lines=1,
                )
            with gr.Column(scale=1):
                generate_btn = gr.Button(
                    "Generate Report",
                    variant="primary",
                    size="lg",
                )

        with gr.Row():
            clear_btn = gr.Button("Clear", variant="secondary", size="sm")

        gr.Markdown("### Report")

        # Rendered markdown view
        report_display = gr.Markdown(
            value="Report will appear here...",
            elem_id="report-display",
        )

        # Raw markdown — copyable
        report_raw = gr.Textbox(
            label="Raw Markdown (copy to save)",
            lines=20,
            interactive=False,
            visible=False,
            elem_id="report-raw",
        )

        show_raw_btn = gr.Button("Show Raw Markdown", variant="secondary", size="sm")

        # ── Event handlers ────────────────────────────────────────
        generate_btn.click(
            fn=generate_handler,
            inputs=[company_input],
            outputs=[report_display, report_raw],
            show_progress="full",
        )

        company_input.submit(
            fn=generate_handler,
            inputs=[company_input],
            outputs=[report_display, report_raw],
            show_progress="full",
        )

        clear_btn.click(
            fn=clear_handler,
            inputs=[],
            outputs=[company_input, report_display, report_raw],
        )

        show_raw_btn.click(
            fn=lambda visible: gr.update(visible=not visible),
            inputs=[gr.State(False)],
            outputs=[report_raw],
        )

    return demo