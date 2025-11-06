
# 🌿 Carbon Emission Tracker Database

**A robust relational database solution built to track individual carbon footprints, automating emission calculations via triggers and generating complex analytical reports using stored procedures and functions.**

***

## 🎯 Project Goal

To serve as the highly efficient, analytical backend for a carbon emission tracking application. This database manages all user data, activity logs, and calculation logic, enabling the Streamlit/Python frontend to display real-time insights into user goals and emission rankings.

***

## 🔑 Key Database Features

| Feature | Implementation | Description |
| :--- | :--- | :--- |
| **Automatic Calculation** | **Triggers (BEFORE INSERT/UPDATE)** | Automatically calculates and stores the `CalculatedEmission` for every log entry, ensuring data accuracy at the source. |
| **Complex Reporting** | **Stored Procedures** | Provides fast, aggregated reports (`GetMonthlyEmissionsByCategory`, `GetActivityRankingByEmission`) that are ideal for rapid display in the Streamlit dashboard. |
| **Business Logic** | **Stored Functions** | Encapsulates core logic, such as checking a user's `CarbonGoal` status (`CheckIfUserMetGoal`). |
| **Streamlined Deployment** | **Single SQL File** | The entire database structure, logic, and sample data are contained in one script for easy setup. |

***

## ⚙️ Setup and Deployment

### 1. Database Deployment (The SQL Backend)

Your entire database structure, logic, and sample data are contained within the `carbon_tracker_full_deployment.sql` file.

1.  **Open your MySQL Client** (e.g., MySQL Workbench, DBeaver, or command line).
2.  **Execute the entire contents of the `carbon_tracker_full_deployment.sql` script.**
    * This script creates the `carbon_tracker` database, all 6 necessary tables, installs 4 stored programs (2 Functions, 2 Procedures), and populates them with seed data.

### 2. Frontend Connection (Streamlit/Python)

Once the database is deployed, your Python application can connect to it using a standard SQL connector library.

* **Essential Credentials:**
    * **Database:** `carbon_tracker`
    * **Host:** `localhost` (or your database server IP)
    * **User/Password:** Your local MySQL credentials

* **Data Interaction Strategy (Why use procedures):**
    Your Python code should primarily use `CALL` statements to fetch complex reports, keeping the calculation logic on the server for maximum efficiency:

  

***

##  Testing and Demonstration

Use these commands directly in your MySQL client to verify the core reporting functionality immediately after deployment.

| Object Type | Name | Demonstration Query |
| :--- | :--- | :--- |
| **Function** | `CheckIfUserMetGoal` | `SELECT CheckIfUserMetGoal(1, 2025, 10);` |
| **Procedure**| `GetMonthlyEmissionsByCategory` | `CALL GetMonthlyEmissionsByCategory(1, 2025, 10);` |
| **Procedure**| `GetActivityRankingByEmission` | `CALL GetActivityRankingByEmission(1, '2025-10-01', '2025-10-31');` |
