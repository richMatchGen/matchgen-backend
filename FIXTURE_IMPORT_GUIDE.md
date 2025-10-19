# Fixture Import System - Complete Guide

## Overview

The new fixture import system allows users to quickly and easily add multiple fixtures to their club through three different methods:

1. **CSV Upload** - Upload a CSV file with fixture data
2. **FA Fulltime Scraper** - Automatically import from FA Fulltime website
3. **Play Cricket API** - Import fixtures from Play Cricket for cricket clubs

## Features Implemented

### Backend API Endpoints

#### 1. CSV Upload Enhancement
- **Endpoint**: `POST /api/content/fixtures/import/csv/`
- **Enhanced Features**:
  - Better error handling and validation
  - Support for multiple date formats
  - Detailed error reporting per row
  - Required vs optional field validation

#### 2. FA Fulltime Scraper
- **Endpoint**: `POST /api/content/fixtures/import/fa-fulltime/`
- **Features**:
  - Web scraping of FA Fulltime team pages
  - Automatic fixture data extraction
  - Support for various page layouts
  - Date parsing for multiple formats

#### 3. Play Cricket API Integration
- **Endpoint**: `POST /api/content/fixtures/import/play-cricket/`
- **Features**:
  - Direct API integration with Play Cricket
  - Automatic fixture fetching
  - Support for cricket-specific data

#### 4. Import Options API
- **Endpoint**: `GET /api/content/fixtures/import-options/`
- **Features**:
  - Returns available import methods
  - Field requirements for each method
  - Sample data formats

### Frontend Components

#### 1. FixtureImportModal Component
- **Location**: `matchgen-frontend/src/components/FixtureImportModal.jsx`
- **Features**:
  - Tabbed interface for different import methods
  - CSV file upload with preview
  - FA Fulltime URL input
  - Play Cricket team ID input
  - Downloadable CSV template
  - Real-time validation and error handling

#### 2. Enhanced FixturesManagement Page
- **Location**: `matchgen-frontend/src/pages/FixturesManagement.jsx`
- **New Features**:
  - "Import Fixtures" button
  - Integration with FixtureImportModal
  - Success/error notifications
  - Automatic refresh after import

## Usage Guide

### CSV Upload Method

1. **Prepare Your Data**:
   - Download the CSV template from the import modal
   - Required columns: `opponent`, `date`
   - Optional columns: `location`, `venue`, `time_start`, `match_type`, `home_away`

2. **Supported Date Formats**:
   - DD/MM/YYYY (e.g., 15/03/2024)
   - DD-MM-YYYY (e.g., 15-03-2024)
   - YYYY-MM-DD (e.g., 2024-03-15)
   - DD/MM/YY (e.g., 15/03/24)
   - DD Month YYYY (e.g., 15 March 2024)

3. **Upload Process**:
   - Click "Import Fixtures" button
   - Select "CSV Upload" tab
   - Choose your CSV file
   - Review the preview
   - Click "Import Fixtures"

### FA Fulltime Scraper Method

1. **Find Your Club's FA Fulltime Page**:
   - Visit https://fulltime.thefa.com
   - Search for your club
   - Copy the team page URL (e.g., https://fulltime.thefa.com/displayTeam.html?id=562720767)

2. **Import Process**:
   - Click "Import Fixtures" button
   - Select "FA Fulltime" tab
   - Paste your club's FA Fulltime URL
   - Click "Import from FA Fulltime"

### Play Cricket API Method

1. **Get Your Team ID**:
   - Visit https://play-cricket.ecb.co.uk
   - Navigate to your club's page
   - Find your team ID in the URL or team settings

2. **Import Process**:
   - Click "Import Fixtures" button
   - Select "Play Cricket" tab
   - Enter your team ID
   - Click "Import from Play Cricket"

## Technical Implementation

### Backend Dependencies Added
- `beautifulsoup4==4.12.2` - For web scraping
- `requests` - Already available for API calls

### New View Classes
- `FAFulltimeScraperView` - Handles FA website scraping
- `PlayCricketAPIView` - Handles Play Cricket API integration
- `EnhancedBulkUploadMatchesView` - Enhanced CSV upload with better validation
- `FixtureImportOptionsView` - Provides import method information

### URL Patterns Added
```python
path("fixtures/import-options/", FixtureImportOptionsView.as_view(), name="fixture-import-options"),
path("fixtures/import/csv/", EnhancedBulkUploadMatchesView.as_view(), name="fixture-import-csv"),
path("fixtures/import/fa-fulltime/", FAFulltimeScraperView.as_view(), name="fixture-import-fa"),
path("fixtures/import/play-cricket/", PlayCricketAPIView.as_view(), name="fixture-import-cricket"),
```

## Error Handling

### CSV Upload Errors
- Missing required columns
- Invalid date formats
- Row-specific error reporting
- File type validation

### FA Fulltime Scraper Errors
- Invalid URL format
- Website accessibility issues
- No fixtures found
- Parsing errors

### Play Cricket API Errors
- Invalid team ID
- API connectivity issues
- No fixtures found
- Authentication errors

## Sample Data

### CSV Template Format
```csv
opponent,date,location,venue,time_start,match_type,home_away
Arsenal,15/03/2024,Emirates Stadium,Home,15:00,League,HOME
Chelsea,22/03/2024,Stamford Bridge,Away,17:30,League,AWAY
```

### FA Fulltime URL Example
```
https://fulltime.thefa.com/displayTeam.html?id=562720767
```

### Play Cricket Team ID Example
```
12345
```

## Benefits

1. **Time Saving**: Import multiple fixtures in seconds instead of adding them one by one
2. **Accuracy**: Reduce manual data entry errors
3. **Flexibility**: Multiple import methods for different data sources
4. **User-Friendly**: Intuitive interface with clear instructions
5. **Error Handling**: Comprehensive validation and error reporting

## Future Enhancements

Potential improvements that could be added:
- Support for more sports APIs
- Bulk fixture editing
- Import scheduling
- Data validation rules
- Custom field mapping
- Import history tracking

## Support

For technical support or questions about the fixture import system, please refer to the API documentation or contact the development team.
