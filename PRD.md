

# **Product Requirements Document: Real-Time KTM Train Status Monitor for Taskade**

## **1. Overview**

This document outlines the functionality of a Python script designed to create and maintain a **live dashboard** for KTM (Keretapi Tanah Melayu Berhad) train statuses within a Taskade project.

The script's primary purpose is to solve the problem of information silos by automatically pulling real-time, public transit data from a government API and pushing it into a collaborative workspace. This provides a persistent, at-a-glance view of the train network's operational status directly within a user's project management tool, eliminating the need to manually check external sources.

The target user is an individual or team using Taskade who requires situational awareness of the KTM train network for logistical planning, daily commutes, or general interest.

## **2. Goals & Objectives**

* **Automate Information Flow:** To create a fully automated, "set-it-and-forget-it" system for monitoring train data.
* **Provide a Single Source of Truth:** To ensure that all updates are reflected in a single, persistent Taskade task, preventing clutter and confusion from multiple new tasks being created.
* **Enhance Data Accessibility:** To present complex GTFS (General Transit Feed Specification) data in a simple, human-readable format.
* **Ensure Timeliness:** To provide fresh data at regular intervals, making the dashboard a reliable source for near real-time information.

---

## **3. Functional Requirements (Features)**

| Feature ID | Feature Name | Description |
| :--- | :--- | :--- |
| **F-01** | **Automated Data Fetching** | The system must automatically connect to the Malaysian government's GTFS Realtime API for KTM vehicle positions. It will request the latest available data feed. |
| **F-02** | **Data Processing & Formatting** | The raw data (in Protocol Buffers format) must be parsed to extract key information. This includes the data's timestamp, the total number of active trains, and for all trains: Train ID, Route ID, Latitude/Longitude, and current speed (converted to km/h). The final output must be formatted into clear, readable Markdown. |
| **F-03** | **Initial Task Creation** | On its very first run, the script must create a **new task** in a specified Taskade project. It will post the formatted train status summary to this new task and then internally store the unique ID of the created task for future use. |
| **F-04** | **Continuous Task Updating** | For all subsequent runs after the first one, the system **must not** create a new task. Instead, it will use the stored task ID to **update the content of the existing task** with the latest formatted train data. This is the core logic that maintains a single, live dashboard. |
| **F-05** | **Scheduled Execution** | The entire process of fetching, formatting, and updating the Taskade task must run automatically every **15 minutes** to ensure the data remains current. |
| **F-06** | **Secure Configuration** | API keys and Project IDs for Taskade must be securely managed using Google Colab's secret management system, not hardcoded into the script. |

---

## **4. User Flow & System Logic**

The system operates based on a stateful, two-stage logic:

**1. First Run (Initialization):**
* The script starts and authenticates with the Taskade API.
* It calls the KTM GTFS API to fetch live train data.
* It formats this data into a Markdown summary.
* It sends a `POST` request to the Taskade API to create a **new** task with the summary.
* It parses the response from Taskade to capture the new task's unique ID.
* This ID is saved in a global variable (`taskade_task_id`).

**2. Subsequent Runs (Update Cycle):**
* After 15 minutes, the scheduler triggers the function again.
* It fetches fresh data from the KTM API and formats it.
* It checks the `taskade_task_id` variable and sees that it now contains an ID.
* It sends a `PUT` request to the Taskade API, targeting the specific task ID, to **overwrite its content** with the new summary.
* This loop repeats every 15 minutes.

In essence, this script transforms a static Taskade task into a dynamic, real-time information dashboard powered by live public transit data.