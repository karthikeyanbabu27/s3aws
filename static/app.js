const dropArea = document.getElementById("drop-area");
const fileInput = document.getElementById("fileInput");
const filePreview = document.getElementById("file-preview");
const uploadContainer = document.getElementById("upload-container");
const uploadForm = document.getElementById("uploadForm");
const uploadButton = document.getElementById("uploadButton");

// Handle click to open file dialog
dropArea.addEventListener("click", () => fileInput.click());

// Handle drag over
dropArea.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropArea.classList.add("dragover");
});

// Handle drag leave
dropArea.addEventListener("dragleave", () => {
    dropArea.classList.remove("dragover");
});

// Handle file drop
dropArea.addEventListener("drop", (e) => {
    e.preventDefault();
    dropArea.classList.remove("dragover");
    fileInput.files = e.dataTransfer.files;
    displayFile(fileInput.files[0]);
});

// Handle file selection
fileInput.addEventListener("change", () => {
    if (fileInput.files.length > 0) {
        displayFile(fileInput.files[0]);
    }
});

// Function to display file name and remove upload option
function displayFile(file) {
    if (file) {
        uploadContainer.innerHTML = `<div class="success-message">✅ File Uploaded: <strong>${file.name}</strong></div>`;
    }
}

// Prevent form submission and use AJAX instead
uploadForm.addEventListener("submit", async (e) => {
    e.preventDefault();

    if (fileInput.files.length === 0) {
        alert("Please select a CSV file first!");
        return;
    }

    const formData = new FormData();
    formData.append("csvFile", fileInput.files[0]);

    uploadButton.textContent = "Uploading...";
    uploadButton.disabled = true;

    try {
        const response = await fetch(uploadForm.action, {
            method: "POST",
            body: formData
        });

        if (!response.ok) {
            throw new Error(await response.text());
        }

        // Remove upload area and show success message
        uploadContainer.innerHTML = `<div class="success-message">✅ File Uploaded: <strong>${fileInput.files[0].name}</strong></div>`;

        // Redirect to result page after successful upload
        window.location.href = response.url;
    } catch (error) {
        alert("Error uploading file: " + error.message);
    } finally {
        uploadButton.textContent = "Upload";
        uploadButton.disabled = false;
    }
});
