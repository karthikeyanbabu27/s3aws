from flask import Flask, request, render_template, redirect, url_for, send_file
import boto3
import os
import json
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from datetime import datetime

app = Flask(__name__)

# S3 Bucket Configurations
CSV_BUCKET = "hackathonwin"
JSON_BUCKET = "macie-job-exports"
JSON_PREFIX = "macie-findings/new.json"  # Folder where JSON files are stored
PDF_BUCKET = "hackathonwin"  # Store generated PDFs in the same bucket

s3 = boto3.client("s3")

@app.route("/")
def index():
    return render_template("upload.html")

@app.route("/upload", methods=["POST"])
def upload_file():
    """Handles CSV file upload and redirects to buffer page before result"""
    if "file" not in request.files:
        return "No file uploaded", 400

    file = request.files["file"]
    if file.filename == "":
        return "No selected file", 400

    file_name, file_extension = os.path.splitext(file.filename)
    
    if file_extension.lower() != ".csv":
        return "Only CSV files are allowed", 400

    # Upload CSV to the hackathon bucket
    s3.upload_fileobj(file, CSV_BUCKET, file.filename)

    # Redirect to buffer page before fetching JSON file
    return redirect(url_for("buffer"))

@app.route("/buffer")
def buffer():
    """Temporary buffer page before showing result"""
    return render_template("buffer.html", result_url=url_for("result"))

@app.route("/result")
def result():
    """Fetches a JSON file, converts it to a PDF, and provides a download link"""
    try:
        json_data, json_file_key = fetch_json_from_s3()

        if json_data is None:
            return "No compliance report found", 404

        # Extract necessary compliance details
        compliance_details = extract_compliance_details(json_data)
        
        # DEBUGGING: Print out the compliance details
        print("Compliance Details:")
        print(json.dumps(compliance_details, indent=2))

        # Generate PDF from JSON data
        pdf_filename = json_file_key.split("/")[-1].replace(".json", ".pdf")
        pdf_content = generate_pdf(compliance_details)

        # Upload the PDF to S3
        s3.upload_fileobj(pdf_content, PDF_BUCKET, pdf_filename)

        # Generate a pre-signed URL for downloading the PDF file
        pdf_url = s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": PDF_BUCKET, "Key": pdf_filename},
            ExpiresIn=3600,  # Link expires in 1 hour
        )

        return render_template("result.html", compliance=compliance_details, file_url=pdf_url)

    except Exception as e:
        print(f"Error processing JSON file: {e}")
        return "Error processing JSON file or file not found", 500

def fetch_json_from_s3():
    """Fetches JSON file from S3 and parses it."""
    try:
        response = s3.list_objects_v2(Bucket=JSON_BUCKET, Prefix=JSON_PREFIX)

        if "Contents" not in response or not response["Contents"]:
            print("No JSON file found in S3!")
            return None, None

        json_file_key = response["Contents"][0]["Key"]

        json_object = s3.get_object(Bucket=JSON_BUCKET, Key=json_file_key)
        json_content = json_object["Body"].read().decode("utf-8")

        parsed_json = json.loads(json_content)
        return parsed_json, json_file_key

    except Exception as e:
        print(f"Error fetching JSON file: {e}")
        return None, None

def extract_compliance_details(json_data):
    """Extracts relevant compliance details from JSON report."""
    report = json_data[0]  # Access the first object in the JSON list
    
    # Print out the raw severity information for debugging
    print("Raw Severity Information:")
    print(json.dumps(report.get("severity", {}), indent=2))
    
    # Determine risk severity 
    severity = report.get("severity", {}).get("description", "Unknown")
    print(f"Extracted Severity: {severity}")
    
    # Risk calculation logic
    risk_counts = {"High": 0, "Medium": 0, "Low": 0}
    
    # Determine risk based on severity
    if severity.lower() == "high":
        risk_counts["High"] = 1
    elif severity.lower() == "medium":
        risk_counts["Medium"] = 1
    else:
        risk_counts["Low"] = 1
    
    print("Risk Counts:", risk_counts)
    
    sensitive_data = report.get("classificationDetails", {}).get("result", {}).get("sensitiveData", [])
    sensitivities = []

    # Categorize sensitivities
    for data in sensitive_data:
        category = data.get("category", "Unknown")
        
        # Risk assessment logic
        if category in ["FINANCIAL", "PERSONAL_HEALTH", "SSN"]:
            risk = "High"
            action = f"Immediately protect {category} information"
        elif category in ["EMAIL", "PHONE", "ADDRESS"]:
            risk = "Medium"
            action = f"Review and secure {category} data handling"
        else:
            risk = "Low"
            action = "Maintain current data protection measures"
        
        risk_counts[risk] += 1
        
        sensitivities.append({
            "type": category,
            "visibility": "Partially Visible",
            "risk": risk,
            "action": action
        })

    # Compliance details dictionary
    compliance_details = {
        "Risk Level": severity,
        "Category": report.get("category", "Unknown"),
        "Findings Count": report.get("count", 0),
        "Description": report.get("description", "No description available"),
        "Last Updated": report.get("updatedAt", "Unknown"),
        
        # Risk Distribution
        "High Risk": risk_counts["High"],
        "Medium Risk": risk_counts["Medium"],
        "Low Risk": risk_counts["Low"],
        
        # Sensitivities for detailed findings
        "Sensitivities": sensitivities,
        
        # Compliance Metrics for Radar Chart (adjust these based on your data)
        "Data Protection": min(100, risk_counts["High"] * 30 + 50),
        "Access Control": min(100, risk_counts["Medium"] * 20 + 60),
        "Security Monitoring": min(100, risk_counts["Low"] * 10 + 70),
        "Privacy": min(100, len(sensitive_data) * 15 + 55),
        "Encryption": min(100, risk_counts["High"] * 25 + 45)
    }
    
    return compliance_details

def generate_pdf(compliance_details):
    """Generates a PDF file from compliance details and returns it as a BytesIO object."""
    pdf_buffer = BytesIO()
    pdf_canvas = canvas.Canvas(pdf_buffer, pagesize=letter)
    pdf_canvas.setFont("Helvetica", 12)

    pdf_canvas.drawString(100, 750, "Compliance Report")
    pdf_canvas.drawString(100, 730, "-" * 50)

    y_position = 700
    for key, value in compliance_details.items():
        # Handle nested structures for Sensitivities
        if key == "Sensitivities":
            pdf_canvas.drawString(100, y_position, f"{key}:")
            y_position -= 20
            for sensitivity in value:
                pdf_canvas.drawString(120, y_position, f"- {sensitivity}")
                y_position -= 20
        else:
            pdf_canvas.drawString(100, y_position, f"{key}: {value}")
            y_position -= 20

    pdf_canvas.save()
    pdf_buffer.seek(0)
    return pdf_buffer

if __name__ == "__main__":
    app.run(debug=True)
