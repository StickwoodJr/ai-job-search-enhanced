# TechTO Jobs URL Reference & API Documentation

## Endpoints

### 1. Search Endpoint
- **URL**: `https://jobs.techto.org/jobs`
- **Method**: `GET`
- **Query Parameters**:
  - `query`: Keyword / role title / technology
  - `location`: Location string (e.g. `Toronto, ON`, `Canada`)
  - `page`: 1-indexed page number

### 2. Embedded JSON State
TechTO (hosted on JBoard) embeds the full structured jobs array in the HTML response:
```javascript
window.jobsList = window.jobsList || [];
window.jobsList = window.jobsList.concat([
  {
    "id": 578956434,
    "title": "Operations Coordinator",
    "employer": { "name": "TechTO", "website": "https://www.techto.org/" },
    "location": "Toronto, Ontario, Canada",
    "job_location": { "name": "Toronto, Ontario, Canada" },
    "posted_at": "2026-08-04T16:37:20.000000Z",
    "job_details_path": "/jobs/578956434-operations-coordinator",
    "min_compensation": "51000.00",
    "max_compensation": "56000.00",
    "compensation_currency": "cad",
    "compensation_time_frame": "annually",
    "description": "<p>...</p>",
    "job_type": { "title": "Full-time" }
  }
]);
```

### 3. Detail Endpoint
- **URL**: `https://jobs.techto.org/jobs/{id}` or `https://jobs.techto.org/jobs/{id}-{slug}`
