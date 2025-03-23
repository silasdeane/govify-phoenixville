import fitz  # PyMuPDF
import os
import glob

# Folder containing the PDF documents
pdf_folder = "/Users/heysilas/Downloads/phoenixville info"

# Find all PDF files in the folder
pdf_files = glob.glob(os.path.join(pdf_folder, "*.pdf"))

# Name of the output text file (adjust as needed)
output_file = "municipal_docs.txt"

combined_text = ""

# Process each PDF file
for pdf_file in pdf_files:
    print(f"Processing: {pdf_file}")
    try:
        doc = fitz.open(pdf_file)  # This should work if PyMuPDF is installed correctly.
    except Exception as e:
        print(f"Error opening {pdf_file}: {e}")
        continue

    combined_text += f"\n\n===== {os.path.basename(pdf_file)} =====\n\n"
    for page in doc:
        combined_text += page.get_text()
    doc.close()

# Write the combined text to the output file
with open(output_file, "w", encoding="utf-8") as f:
    f.write(combined_text)

print(f"All PDF content has been combined into {output_file}.")
