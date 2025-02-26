from flask import render_template, request, redirect, flash
from flask_login import login_required
import cv2
import numpy as np
from core.prescription.ocr_engine import extract_text
from utils.file_handler import allowed_file  # Ensure this function is implemented correctly

@app.route('/ocr-prescription', methods=['GET', 'POST'])
@login_required
def ocr_prescription():
    if request.method == 'POST':
        # Check if a file was uploaded
        if 'prescription_image' not in request.files:
            flash('No file uploaded', 'error')
            return redirect(request.url)

        file = request.files['prescription_image']

        if file.filename == '':
            flash('No file selected', 'error')
            return redirect(request.url)

        if file and allowed_file(file.filename):
            try:
                # Read image from file
                image = cv2.imdecode(
                    np.frombuffer(file.read(), np.uint8),
                    cv2.IMREAD_COLOR
                )

                is_handwritten = request.form.get('is_handwritten', 'false').lower() == 'true'

                # Call OCR engine
                result = extract_text(image, is_handwritten=is_handwritten)

                return render_template('ocr_results.html', result=result)
            except Exception as e:
                flash(f'Error processing image: {str(e)}', 'error')
                return redirect(request.url)

    return render_template('ocr_upload.html')
