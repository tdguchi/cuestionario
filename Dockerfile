FROM python:3.9-windowsservercore

# Install wkhtmltopdf - Using a Windows compatible version
RUN powershell -Command \
    Invoke-WebRequest -Uri https://github.com/wkhtmltopdf/packaging/releases/download/0.12.6-1/wkhtmltox-0.12.6-1.msvc2015-win64.exe -OutFile wkhtmltox.exe ; \
    Start-Process wkhtmltox.exe -ArgumentList '/S' -Wait ; \
    Remove-Item wkhtmltox.exe ; \
    setx PATH "%PATH%;C:\Program Files\wkhtmltopdf\bin"

# Set working directory
WORKDIR C:/app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Expose port
EXPOSE 5000

# Command to run the application
CMD ["python", "app.py"]
