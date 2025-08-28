# GPS Server Setup Guide

Follow these steps to set up the project using Anaconda and run the development server.

---

## 1. Install Anaconda
Download and install Anaconda from [https://www.anaconda.com/](https://www.anaconda.com/).

---

## 2. Create a new environment
Open your terminal and run:

```bash
conda create -n gpsserver python=3.12
```

This will create a new environment named `gpsserver` with Python 3.12.

---

## 3. Activate the environment
```bash
conda activate gpsserver
```

---

## 4. Install project dependencies
If you have a `requirements.txt` file:

```bash
pip install -r requirements.txt
```

---

## 5. Run database migrations
```bash
python manage.py migrate
```

This will set up the database and create all required tables.

---

## 6. Create a superuser
```bash
python manage.py createsuperuser
```

Follow the prompts to set username, email, and password.

---

## 7. Run the development server
```bash
python manage.py runserver
```

Your server will now be accessible at [http://127.0.0.1:8000/](http://127.0.0.1:8000/).  
The admin panel is available at [http://127.0.0.1:8000/admin/](http://127.0.0.1:8000/admin/) for manual GPS frame uploads.

---

# Bulk Upload Test Cases

Use these test cases to verify the behavior of the manual frame upload in the admin panel. Paste the frames into the textarea form for testing.

## To go into the bulk update admin view enter the registered FramwRaw model and a bulk update button appears in the top right corner

---


## 1. Valid Frames

These frames are all valid. Each line should create a `FrameRaw` and a `Position`.

```text
$IGX,1.2,123456789012345,001,210827,120000,3456.7890,N,09812.8955,W,60.5,180,15.0,3,12,0.5,1234.5,50.0,12.3,1A2B,ODO_MODE=ABS;TEMP_C=36.5;DRIVER_ID=AA11-BB22;FW=2025.08.1*54
$IGX,1.2,987654321098765,002,210827,121500,4032.1234,S,07456.7890,E,45.0,90,10.5,2,8,1.0,5678.9,40.0,11.5,0F3C,ODO_MODE=TRIP;TEMP_C=28.0;DRIVER_ID=CC33-DD44;FW=2025.08.2*17
$IGX,1.2,192837465091827,003,210827,123000,5123.4567,N,00123.4567,W,30.0,270,5.0,1,5,0.3,987.6,35.0,9.8,2B1D,ODO_MODE=ABS;TEMP_C=32.5;DRIVER_ID=EE55-FF66;FW=2025.08.3*5F
```

---

## 2. Out-of-Range Values

This frame has an invalid latitude (latitude cannot exceed 90°). It should create a `FrameRaw` but **no `Position`**, and the error field should be populated.

```text
$IGX,1.2,555555555555555,006,210828,140000,9123.4567,N,01234.5678,E,50.0,90,10.0,3,10,1.0,1000.0,50.0,12.0,1F2E,ODO_MODE=ABS;TEMP_C=25.0;DRIVER_ID=ZZ99-YY88;FW=2025.08.5*7D
```

---

## 3. Duplicate `device+seq`

This dataset has 3 frames, but one of them is a duplicate by `device+seq`. Only 2 `Position` objects should be created. The duplicate should be logged as an error.

```text
$IGX,1.2,123456789012345,001,210827,120000,3456.7890,N,09812.8955,W,60.5,180,15.0,3,12,0.5,1234.5,50.0,12.3,1A2B,ODO_MODE=ABS;TEMP_C=36.5;DRIVER_ID=AA11-BB22;FW=2025.08.1*54
$IGX,1.2,987654321098765,002,210827,121500,4032.1234,S,07456.7890,E,45.0,90,10.5,2,8,1.0,5678.9,40.0,11.5,0F3C,ODO_MODE=TRIP;TEMP_C=28.0;DRIVER_ID=CC33-DD44;FW=2025.08.2*17
$IGX,1.2,123456789012345,001,210827,120000,3456.7890,N,09812.8955,W,60.5,180,15.0,3,12,0.5,1234.5,50.0,12.3,1A2B,ODO_MODE=ABS;TEMP_C=36.5;DRIVER_ID=AA11-BB22;FW=2025.08.1*54
```

---


#### 4. Invalid Checksum

Checksum is incorrect, frame is rejected:

```text
$IGX,1.2,123456789012345,001,210827,120000,3456.7890,N,09812.8955,W,60.5,180,15.0,3,12,0.5,1234.5,50.0,12.3,1A2B,ODO_MODE=ABS;TEMP_C=36.5;DRIVER_ID=AA11-BB22;FW=2025.08.1*00
```

- `FrameRaw.checksum_valid = False`
- No Position created
- Error logged
- But Device is created

**Notes:**

- Each frame should create a `FrameRaw` object regardless of validity.
- Valid frames create a `Position`.
- Invalid frames populate `FrameRaw.error` and generate a `ProcessingLog`.
- Duplicate `device+seq` frames are rejected for `Position` creation but still stored as `FrameRaw` with an error log.
