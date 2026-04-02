import pandas as pd
import numpy as np
import json
import os
from typing import Dict, List, Any, Tuple
from django.conf import settings
from django.core.files.uploadedfile import UploadedFile
from dashboard.models import DatasetInfo, UploadedFile as FileModel
import sqlparse
from openpyxl import load_workbook


class DataProcessorService:
    """Service for processing uploaded data files"""
    
    def __init__(self):
        self.supported_formats = ['.xlsx', '.xls', '.csv', '.sql']
    
    def process_uploaded_file(self, file_obj: FileModel) -> DatasetInfo:
        """Process uploaded file and create dataset info"""
        try:
            file_path = file_obj.file.path
            file_extension = os.path.splitext(file_obj.file_name)[1].lower()
            
            if file_extension in ['.xlsx', '.xls']:
                df = self._process_excel_file(file_path)
            elif file_extension == '.csv':
                df = self._process_csv_file(file_path)
            elif file_extension == '.sql':
                df = self._process_sql_file(file_path)
            else:
                raise ValueError(f"Unsupported file format: {file_extension}")
            
            # Create dataset info
            dataset_info = self._create_dataset_info(df, file_obj)
            file_obj.processed = True
            file_obj.save()
            
            return dataset_info
            
        except Exception as e:
            file_obj.processing_error = str(e)
            file_obj.save()
            raise e
    
    def _process_excel_file(self, file_path: str) -> pd.DataFrame:
        """Process Excel files"""
        try:
            # Try to read with openpyxl engine first
            df = pd.read_excel(file_path, engine='openpyxl')
        except Exception:
            try:
                # Fallback to xlrd for older files
                df = pd.read_excel(file_path, engine='xlrd')
            except Exception:
                # Last resort - try default engine
                df = pd.read_excel(file_path)
        
        return self._clean_dataframe(df)
    
    def _process_csv_file(self, file_path: str) -> pd.DataFrame:
        """Process CSV files"""
        try:
            # Try different encodings
            encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
            df = None
            
            for encoding in encodings:
                try:
                    df = pd.read_csv(file_path, encoding=encoding)
                    break
                except UnicodeDecodeError:
                    continue
            
            if df is None:
                raise ValueError("Could not decode CSV file with any supported encoding")
            
            return self._clean_dataframe(df)
            
        except Exception as e:
            raise ValueError(f"Error processing CSV file: {str(e)}")
    
    def _process_sql_file(self, file_path: str) -> pd.DataFrame:
        """Process SQL files - extract data from INSERT statements"""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                sql_content = file.read()
            
            # Parse SQL statements
            statements = sqlparse.split(sql_content)
            
            # Look for CREATE TABLE and INSERT statements
            table_data = []
            columns = []
            
            for statement in statements:
                parsed = sqlparse.parse(statement)[0]
                
                # Extract column names from CREATE TABLE
                if 'CREATE TABLE' in statement.upper():
                    columns = self._extract_columns_from_create_table(statement)
                
                # Extract data from INSERT statements
                elif 'INSERT INTO' in statement.upper():
                    values = self._extract_values_from_insert(statement)
                    if values:
                        table_data.extend(values)
            
            if not table_data:
                raise ValueError("No INSERT statements found in SQL file")
            
            if not columns:
                # Generate generic column names if no CREATE TABLE found
                if table_data:
                    columns = [f'column_{i+1}' for i in range(len(table_data[0]))]
            
            df = pd.DataFrame(table_data, columns=columns)
            return self._clean_dataframe(df)
            
        except Exception as e:
            raise ValueError(f"Error processing SQL file: {str(e)}")
    
    def _extract_columns_from_create_table(self, statement: str) -> List[str]:
        """Extract column names from CREATE TABLE statement"""
        columns = []
        try:
            # Simple regex to extract column names
            import re
            pattern = r'\(([^)]+)\)'
            match = re.search(pattern, statement)
            if match:
                columns_part = match.group(1)
                for line in columns_part.split(','):
                    line = line.strip()
                    if line and not line.upper().startswith('PRIMARY') and not line.upper().startswith('FOREIGN'):
                        column_name = line.split()[0].strip('`"[]')
                        columns.append(column_name)
        except Exception:
            pass
        return columns
    
    def _extract_values_from_insert(self, statement: str) -> List[List]:
        """Extract values from INSERT statement"""
        values = []
        try:
            import re
            # Match VALUES (...), (...), ...
            pattern = r'VALUES\s*\(([^)]+)\)'
            matches = re.findall(pattern, statement, re.IGNORECASE)
            
            for match in matches:
                row_values = []
                # Split by comma but handle quoted strings
                parts = self._split_values(match)
                for part in parts:
                    part = part.strip().strip('\'"')
                    # Try to convert to appropriate type
                    if part.lower() == 'null':
                        row_values.append(None)
                    elif part.isdigit():
                        row_values.append(int(part))
                    else:
                        try:
                            row_values.append(float(part))
                        except ValueError:
                            row_values.append(part)
                values.append(row_values)
        except Exception:
            pass
        return values
    
    def _split_values(self, values_str: str) -> List[str]:
        """Split VALUES string by comma, respecting quotes"""
        values = []
        current_value = ""
        in_quotes = False
        quote_char = None
        
        for char in values_str:
            if char in ['"', "'"] and not in_quotes:
                in_quotes = True
                quote_char = char
                current_value += char
            elif char == quote_char and in_quotes:
                in_quotes = False
                quote_char = None
                current_value += char
            elif char == ',' and not in_quotes:
                values.append(current_value.strip())
                current_value = ""
            else:
                current_value += char
        
        if current_value.strip():
            values.append(current_value.strip())
        
        return values
    
    def _clean_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean and prepare dataframe"""
        # Remove completely empty rows and columns
        df = df.dropna(how='all').dropna(axis=1, how='all')
        
        # Clean column names
        df.columns = df.columns.astype(str)
        df.columns = [col.strip().replace(' ', '_').replace('\n', '_') for col in df.columns]
        
        # Remove duplicate column names
        seen = set()
        new_columns = []
        for col in df.columns:
            if col in seen:
                counter = 1
                while f"{col}_{counter}" in seen:
                    counter += 1
                new_col = f"{col}_{counter}"
                new_columns.append(new_col)
                seen.add(new_col)
            else:
                new_columns.append(col)
                seen.add(col)
        df.columns = new_columns
        
        return df
    
    def _create_dataset_info(self, df: pd.DataFrame, file_obj: FileModel) -> DatasetInfo:
        """Create DatasetInfo object from processed dataframe"""
        
        # Analyze columns
        columns_info = []
        numeric_columns = []
        categorical_columns = []
        date_columns = []
        
        for col in df.columns:
            col_info = {
                'name': col,
                'dtype': str(df[col].dtype),
                'null_count': int(df[col].isnull().sum()),
                'unique_count': int(df[col].nunique())
            }
            
            # Determine column type
            if pd.api.types.is_numeric_dtype(df[col]):
                col_info['type'] = 'numeric'
                numeric_columns.append(col)
            elif pd.api.types.is_datetime64_any_dtype(df[col]):
                col_info['type'] = 'datetime'
                date_columns.append(col)
            else:
                # Try to detect date columns
                if self._is_date_column(df[col]):
                    col_info['type'] = 'datetime'
                    date_columns.append(col)
                else:
                    col_info['type'] = 'categorical'
                    categorical_columns.append(col)
            
            columns_info.append(col_info)
        
        # Calculate summary statistics for numeric columns
        summary_stats = {}
        if numeric_columns:
            numeric_summary = df[numeric_columns].describe().to_dict()
            summary_stats = {
                'numeric_summary': numeric_summary,
                'correlations': df[numeric_columns].corr().to_dict() if len(numeric_columns) > 1 else {}
            }
        
        # Create and save DatasetInfo
        dataset_info = DatasetInfo.objects.create(
            uploaded_file=file_obj,
            columns=columns_info,
            row_count=len(df),
            column_count=len(df.columns),
            numeric_columns=numeric_columns,
            categorical_columns=categorical_columns,
            date_columns=date_columns,
            summary_stats=summary_stats
        )
        
        # Cache the dataframe as a CSV for later use
        cache_dir = os.path.join(settings.MEDIA_ROOT, 'cache')
        cache_path = os.path.join(cache_dir, f'{file_obj.id}_processed.csv')
        os.makedirs(cache_dir, exist_ok=True)
        df.to_csv(cache_path, index=False)
        
        return dataset_info
    
    def _is_date_column(self, series: pd.Series) -> bool:
        """Check if a series contains date-like data"""
        try:
            # Try to parse a sample of non-null values
            sample = series.dropna().head(10)
            if len(sample) == 0:
                return False
            
            parsed_count = 0
            for value in sample:
                try:
                    pd.to_datetime(value)
                    parsed_count += 1
                except (ValueError, TypeError):
                    pass
            
            # If more than 70% can be parsed as dates, consider it a date column
            return parsed_count / len(sample) > 0.7
        except Exception:
            return False
    
    def get_cached_dataframe(self, dataset_info: DatasetInfo) -> pd.DataFrame:
        """Get cached processed dataframe"""
        cache_path = os.path.join(settings.MEDIA_ROOT, 'cache', f'{dataset_info.uploaded_file.id}_processed.csv')
        if os.path.exists(cache_path):
            return pd.read_csv(cache_path)
        else:
            # Reprocess if cache doesn't exist
            return self._process_uploaded_file_to_df(dataset_info.uploaded_file)
    
    def _process_uploaded_file_to_df(self, file_obj: FileModel) -> pd.DataFrame:
        """Process uploaded file and return dataframe"""
        file_path = file_obj.file.path
        file_extension = os.path.splitext(file_obj.file_name)[1].lower()
        
        if file_extension in ['.xlsx', '.xls']:
            return self._process_excel_file(file_path)
        elif file_extension == '.csv':
            return self._process_csv_file(file_path)
        elif file_extension == '.sql':
            return self._process_sql_file(file_path)
        else:
            raise ValueError(f"Unsupported file format: {file_extension}")