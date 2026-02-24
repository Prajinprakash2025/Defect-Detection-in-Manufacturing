# Defect Detection System

## Project Overview
This project is an AI-powered defect detection system designed for industrial quality control. It uses computer vision to identify defects (e.g., scratches, dents) on manufactured parts in real-time. The system includes a comprehensive dashboard for monitoring inspection results, managing users, and generating reports.

## System Architecture & Data Flow
The system operates on a continuous **Feedback Loop** designed to improve accuracy over time:
1.  **Input**: Images are captured and uploaded by Inspectors.
2.  **Processing**: The AI model analyzes predictions.
3.  **Visualization**: Results are displayed on the Dashboard with specific Confidence Scores.
4.  **Feedback (Human-in-the-Loop)**: Admins review low-confidence or disputed results. Corrections (e.g., marking a missed scratch) are saved to the database.
5.  **Retraining**: These "Verified" images update the dataset, which is used to retrain the AutoML model, closing the loop.

## Technical Detail: Model Calibration
To ensure high precision and minimize false positives, particularly on **clean metal surfaces** which can suffer from glare/reflection, the AI model has been carefully calibrated.
- **Confidence Threshold**: Set to **0.85**. This strict threshold ensures that the system only flags a defect when it is highly confident.
- **Precision Optimization**: By enforcing this 85% confidence requirement, we significantly reduce "False Alarms" where light reflections on clean metal might otherwise be mistaken for scratches.
- **Logic**: Any detection with a confidence score below 0.85 is automatically discarded or marked for review, preventing minor noise from cluttering the defect log.

## Workflow: Human-in-the-Loop (HITL) Logic
The system incorporates a robust "Human-in-the-Loop" verification module to handle edge cases and improve trustworthiness.
-   **Manual Override**: An Admin can examine any inspection record. If the AI misses a subtle scratch (False Negative), the Admin uses the **'Verify Result'** button to manually toggle the status from 'Non-Defective' to 'Defective'.
-   **Database Tagging**: When an override occurs, the system flags this specific image record in the database as `verified_by_admin=True` and `is_training_candidate=True`.
-   **Impact**: This distinct tagging allows us to easily export a "Hard Negative" dataset for focused model retraining.

## Security: Role-Based Access Control (RBAC)
Access is strictly controlled via a hierarchical permission system:

### 1. Admin (System Owner)
-   **Permissions**: Full control over the entire system.
-   **Capabilities**:
    -   **User Management**: Create/Edit/Delete users and assign roles.
    -   **Inventory Control**: Manage Product and Batch definitions.
    -   **Verification**: The *only* role authorized to override AI inspection results (HITL).
    -   **System Settings**: View and modify global configurations.

### 2. Manager (Oversight)
-   **Permissions**: Read-Only access to operational data; Full access to Analytics.
-   **Capabilities**:
    -   **Dashboard**: View all team metrics and trends.
    -   **Reporting**: Generate and export PDF/Excel reports.
    -   **Inspections**: View all inspections but *cannot* modify results.

### 3. Inspector (Front-line)
-   **Permissions**: Write access for Uploads; Read access for own history.
-   **Capabilities**:
    -   **Upload**: Submit new images for defect detection.
    -   **My History**: View a list of their own past inspections.
    -   **Restrictions**: No access to Analytics, User Management, or System Settings.

## Scalability: AutoML Retraining
The system is designed to get smarter over time.
-   **Data Tagging**: Every time an Admin manually corrects an inspection result, that image is automatically tagged as "High-Value Training Data".
-   **Retraining**: These verified images are collected to form a high-quality dataset for the next round of AutoML model training, creating a positive feedback loop that continuously improves accuracy.

## Export & Reporting
The system supports generating PDF and Excel reports for shift summaries, defect rates, and individual inspection details.
