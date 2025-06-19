import fitz  # PyMuPDF
import click


@click.group(name="file")
def file():
    pass 

@file.command()
@click.argument('input_oxps', type=click.Path(exists=True))
@click.argument('output_pdf', type=click.Path())
def oxps_to_pdf(input_oxps, output_pdf):
    """Converts an OXPS file (INPUT_OXPS) to a PDF file (OUTPUT_PDF)."""
    try:
        # Open the OXPS file
        oxps_document = fitz.open(input_oxps)

        # Convert to PDF bytes
        pdf_bytes = oxps_document.convert_to_pdf()

        # Open the PDF bytes as a new PDF document
        pdf_document = fitz.open("pdf", pdf_bytes)

        # Save the PDF document to a file
        pdf_document.save(output_pdf)

        click.echo(f"Successfully converted '{input_oxps}' to '{output_pdf}'")

    except Exception as e:
        click.echo(f"Error converting file: {e}", err=True)

if __name__ == '__main__':
    file()
