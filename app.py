from flask import Flask, render_template, request, send_file,redirect, flash
from PyPDF2 import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.pagesizes import A4
import io
from PIL import Image
import os

app = Flask(__name__)
app.secret_key = 'letterhead_app_secret_key'

# Configure upload folder
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # Check if the post request has the file part
        if 'pdf_file' not in request.files:
            flash('No file part')
            return redirect(request.url)

        pdf_file = request.files['pdf_file']

        # If user does not select file, browser also
        # submit an empty part without filename
        if pdf_file.filename == '':
            flash('No selected file')
            return redirect(request.url)

        udin_text = request.form['udin_text']
        top_margin = int(request.form['top_margin'])
        format_type = request.form['format_type']

        if pdf_file and udin_text:
            # Extract the 2nd to 7th characters to determine the letterhead
            udin_substring = udin_text[2:8]
            if udin_substring == "188808":
                letterhead_file = "static/letterhead/RNA.png"
            elif udin_substring == "627790":
                letterhead_file = "static/letterhead/PTA.png"
            elif udin_substring == "631662":
                letterhead_file = "static/letterhead/NSA.png"
            else:
                flash("The UDIN does not match any known letterhead. Please check the number.")
                return redirect(request.url)

            # Process the PDF directly from request data instead of saving to disk
            pdf_data = pdf_file.read()
            pdf_stream = io.BytesIO(pdf_data)

            # Process the PDF with appropriate function
            if format_type == "old":
                processed_pdf = add_letterhead_to_pdf_old(pdf_stream, letterhead_file, top_margin)
            else:
                processed_pdf = add_letterhead_to_pdf_new(pdf_stream, letterhead_file, top_margin)

            # Return the processed PDF as a downloadable file
            output = io.BytesIO(processed_pdf)
            output.seek(0)
            return send_file(
                output,
                mimetype='application/pdf',
                as_attachment=True,
                download_name='output_letterhead.pdf'
            )

    return render_template('index.html')


def add_letterhead_to_pdf_new(pdf_stream, letterhead_image_file, top_margin):
    # Read the main PDF
    main_pdf_reader = PdfReader(pdf_stream)
    pdf_writer = PdfWriter()

    # Set A4 paper size dimensions (in points)
    a4_width, a4_height = A4  # This gives dimensions in points (1 inch = 72 points)

    # Open the letterhead image and get its dimensions
    img = Image.open(letterhead_image_file)
    img_width, img_height = img.size

    # Calculate the aspect ratio of the image
    aspect_ratio = img_width / img_height

    # Calculate the letterhead's display width and height, keeping the width equal to the A4 page width
    width = a4_width  # Fit the letterhead to the full width of the A4 page
    height = width / aspect_ratio

    # Create a temporary PDF for the letterhead
    packet = io.BytesIO()
    can = canvas.Canvas(packet, pagesize=A4)

    # Draw the image at the top of the first page, accounting for the top margin
    can.drawImage(letterhead_image_file, 0, a4_height - height - top_margin, width=width, height=height)

    can.save()
    packet.seek(0)

    # Read the overlay with the letterhead
    overlay_reader = PdfReader(packet)
    overlay_page = overlay_reader.pages[0]

    # Get the first page of the main PDF and merge the letterhead
    first_page = main_pdf_reader.pages[0]
    first_page.merge_page(overlay_page)
    pdf_writer.add_page(first_page)

    # Add the rest of the pages without any letterhead overlay
    for page_number in range(1, len(main_pdf_reader.pages)):
        pdf_writer.add_page(main_pdf_reader.pages[page_number])

    # Save the new PDF with the letterhead only on the first page
    output_pdf = io.BytesIO()
    pdf_writer.write(output_pdf)
    output_pdf.seek(0)

    return output_pdf.getvalue()


def add_letterhead_to_pdf_old(pdf_stream, letterhead_image_file, top_margin):
    main_pdf_reader = PdfReader(pdf_stream)
    pdf_writer = PdfWriter()

    # Open the image and get its dimensions
    img = Image.open(letterhead_image_file)
    img_width, img_height = img.size

    # Calculate the aspect ratio
    aspect_ratio = img_width / img_height

    # Calculate the width and height based on the aspect ratio
    width = letter[0]
    height = width / aspect_ratio

    # Create a temporary PDF for the letterhead top part
    packet = io.BytesIO()
    can = canvas.Canvas(packet, pagesize=letter)

    # Draw the image at the top of the page with margin
    can.drawImage(letterhead_image_file, 0, letter[1] - height - top_margin, width=width, height=height)

    can.showPage()
    can.save()
    packet.seek(0)
    overlay_reader = PdfReader(packet)
    overlay_page = overlay_reader.pages[0]

    for page_number in range(len(main_pdf_reader.pages)):
        page = main_pdf_reader.pages[page_number]
        page.merge_page(overlay_page)
        pdf_writer.add_page(page)

    output_pdf = io.BytesIO()
    pdf_writer.write(output_pdf)

    return output_pdf.getvalue()


if __name__ == '__main__':
    app.run(debug=True)