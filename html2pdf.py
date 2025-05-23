from playwright.sync_api import sync_playwright, Error as PlaywrightError
import os

def convert_html_to_pdf_playwright(html_file_path, pdf_file_path, viewport_width=1920, viewport_height=1080):
    """
    Converts an HTML file to a PDF file using Playwright.

    Args:
        html_file_path (str): The path to the input HTML file.
        pdf_file_path (str): The path where the output PDF file will be saved.
        viewport_width (int): The width of the viewport for rendering.
        viewport_height (int): The height of the viewport for rendering.

    Returns:
        bool: True if conversion was successful, False otherwise.
    """
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()

            page.set_viewport_size({"width": viewport_width, "height": viewport_height})
            print(f"Set viewport size to: {viewport_width}x{viewport_height}")

            abs_html_path = os.path.abspath(html_file_path)
            file_uri = f"file:///{abs_html_path.replace(os.sep, '/')}"

            page.goto(file_uri, wait_until="networkidle")

            page.pdf(path=pdf_file_path, print_background=True)

            browser.close()
            print(f"Successfully converted '{html_file_path}' to '{pdf_file_path}' using Playwright.")
            return True
    except PlaywrightError as e:
        print(f"Playwright specific error during PDF conversion: {e}")
        print("Ensure Playwright is installed correctly and browser binaries are downloaded (run 'playwright install').")
        return False
    except FileNotFoundError:
        print(f"Error: The HTML file '{html_file_path}' was not found.")
        return False
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return False


if __name__ == "__main__":
    input_html = "STT Performance Analysis Report.html"
    output_pdf = "STT Performance Analysis Report (Preview).pdf"
    
    custom_viewport_width = 2560
    custom_viewport_height = 1440

    if convert_html_to_pdf_playwright(input_html, output_pdf, viewport_width=custom_viewport_width, viewport_height=custom_viewport_height):
        print(f"Playwright PDF conversion successful with viewport {custom_viewport_width}x{custom_viewport_height}!")
    else:
        print("Playwright PDF conversion failed. Please check the error messages above.")

