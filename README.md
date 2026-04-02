# Data Dashboard Platform

A powerful web-based platform for uploading data files (Excel, CSV, SQL) and creating interactive dashboards with visualizations.

## Features

- **Multiple File Format Support**: Upload Excel (.xlsx, .xls), CSV, and SQL files
- **Automatic Data Processing**: Intelligent column type detection and data analysis
- **Interactive Charts**: Create bar charts, line graphs, pie charts, scatter plots, histograms, and box plots
- **Responsive Dashboards**: Build comprehensive dashboards with multiple visualizations
- **User Management**: Secure user authentication and data isolation
- **Real-time Visualization**: Dynamic chart updates and filtering

## Technology Stack

- **Backend**: Django 5.2.5, Python 3.x
- **Frontend**: HTML5, CSS3, JavaScript (ES6+), Bootstrap 5.3
- **Charting**: Chart.js
- **Data Processing**: Pandas, NumPy, OpenPyXL, SQLParse
- **Database**: SQLite (development), PostgreSQL (production ready)

## Installation & Setup

### Prerequisites

- Python 3.8 or higher
- pip (Python package installer)

### Installation Steps

1. **Clone or download the project**
   ```bash
   cd /path/to/Dashboard
   ```

2. **Create virtual environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\\Scripts\\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run database migrations**
   ```bash
   python manage.py migrate
   ```

5. **Create superuser (optional)**
   ```bash
   python manage.py createsuperuser
   ```

6. **Start development server**
   ```bash
   python manage.py runserver
   ```

7. **Access the application**
   Open your browser and go to: `http://127.0.0.1:8000`

## Usage Guide

### 1. User Registration/Login
- Create an account or login with existing credentials
- Each user has their own isolated data space

### 2. Upload Data Files
- Navigate to "Upload Data" section
- Drag & drop or select files (Excel, CSV, or SQL)
- Files are automatically processed and analyzed
- View detailed dataset information after processing

### 3. Create Dashboards
- Click "Create Dashboard" for any processed dataset
- Give your dashboard a name and description
- Add various chart types based on your data

### 4. Add Charts
- Choose from multiple chart types:
  - **Bar Chart**: Great for categorical data comparison
  - **Line Chart**: Perfect for time series and trends
  - **Pie Chart**: Show proportions and percentages
  - **Scatter Plot**: Explore relationships between variables
  - **Histogram**: Display data distribution
  - **Box Plot**: Show statistical summaries

### 5. Customize Visualizations
- Select X and Y axis columns
- Choose aggregation methods (count, sum, average, etc.)
- Apply filters to focus on specific data subsets

## File Format Requirements

### Excel Files (.xlsx, .xls)
- Should contain structured data with column headers
- Multiple sheets supported (first sheet is processed)
- Mixed data types are automatically detected

### CSV Files (.csv)
- Comma-separated values with headers
- UTF-8 encoding preferred
- Alternative encodings automatically detected

### SQL Files (.sql)
- Must contain CREATE TABLE and INSERT statements
- Data is extracted from INSERT statements
- Column names derived from CREATE TABLE or auto-generated

## API Endpoints

The platform provides REST API endpoints for programmatic access:

- `POST /upload/handle/` - Upload and process files
- `GET /api/dataset/{id}/columns/` - Get dataset column information
- `POST /api/dashboard/{id}/chart/add/` - Add chart to dashboard
- `DELETE /api/chart/{id}/delete/` - Delete chart
- `GET /api/chart/{id}/data/` - Get chart data

## Project Structure

```
Dashboard/
├── dashboard_platform/          # Django project settings
│   ├── settings.py             # Main configuration
│   ├── urls.py                 # URL routing
│   └── wsgi.py                 # WSGI configuration
├── dashboard/                   # Main Django app
│   ├── models.py               # Database models
│   ├── views.py                # View controllers
│   ├── urls.py                 # App URL patterns
│   ├── admin.py                # Admin interface
│   ├── services/               # Business logic services
│   │   ├── data_processor.py   # File processing service
│   │   └── chart_service.py    # Chart generation service
│   └── templatetags/           # Custom template filters
├── templates/                   # HTML templates
│   ├── base.html               # Base template
│   ├── dashboard/              # Dashboard templates
│   └── registration/           # Auth templates
├── static/                      # Static files
│   ├── css/style.css           # Custom styles
│   └── js/                     # JavaScript files
├── media/                       # User uploaded files
├── requirements.txt            # Python dependencies
└── manage.py                   # Django management script
```

## Security Features

- CSRF protection on all forms
- User authentication required for data access
- File type validation and size limits
- Secure file upload handling
- User data isolation

## Performance Considerations

- File size limit: 100MB per upload
- Chart data points limited for performance
- Cached processed data for faster dashboard loading
- Pagination for large file lists

## Troubleshooting

### Common Issues

1. **File Upload Fails**
   - Check file format (must be .xlsx, .xls, .csv, or .sql)
   - Ensure file size is under 100MB
   - Verify file is not corrupted

2. **Charts Not Displaying**
   - Ensure dataset has been processed successfully
   - Check that columns contain appropriate data types
   - Verify JavaScript is enabled in browser

3. **Processing Errors**
   - Check file encoding (UTF-8 recommended)
   - Ensure Excel files have data in first sheet
   - Verify SQL files contain valid INSERT statements

### Environment Issues

- Ensure virtual environment is activated
- Check all dependencies are installed
- Verify database migrations are applied
- Confirm static files are being served

## Production Deployment

For production deployment, consider:

1. **Security Settings**
   - Set `DEBUG = False`
   - Configure `ALLOWED_HOSTS`
   - Use environment variables for secrets

2. **Database**
   - Switch to PostgreSQL or MySQL
   - Configure database connection pooling

3. **Static Files**
   - Configure static file serving
   - Use CDN for better performance

4. **Web Server**
   - Use Gunicorn or uWSGI
   - Configure reverse proxy (Nginx)

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is open source and available under the MIT License.

## Support

For issues or questions:
1. Check the troubleshooting section
2. Review the error logs in the browser console
3. Ensure all dependencies are correctly installed
4. Verify file formats and sizes meet requirements

---

Built with ❤️ using Django and Chart.js