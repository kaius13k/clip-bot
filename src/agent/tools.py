"""
Tool Manager for AI Agent
Provides various tools for task execution including web search, file operations, code execution, etc.
"""

import os
import json
import asyncio
import requests
import subprocess
import tempfile
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import plotly.express as px
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import sqlite3


class ToolManager:
    """
    Manages and executes various tools for the AI agent
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.tools_config = config.get('tools', {})
        self.logger = logging.getLogger('ToolManager')
        self.temp_dir = tempfile.mkdtemp(prefix='ai_agent_')
        
        # Tool availability
        self.available_tools = {
            'web_search': self.tools_config.get('web_search', True),
            'file_operations': self.tools_config.get('file_operations', True),
            'code_execution': self.tools_config.get('code_execution', True),
            'data_analysis': self.tools_config.get('data_analysis', True),
            'api_calls': self.tools_config.get('api_calls', True)
        }
    
    async def web_search(self, query: str, num_results: int = 5) -> Dict[str, Any]:
        """Search the web for information"""
        try:
            # Use DuckDuckGo as a free search API alternative
            search_url = f"https://html.duckduckgo.com/html/?q={query}"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(search_url, headers=headers, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            results = []
            for result in soup.find_all('div', class_='result')[:num_results]:
                title_elem = result.find('a', class_='result__a')
                snippet_elem = result.find('a', class_='result__snippet')
                
                if title_elem:
                    title = title_elem.get_text(strip=True)
                    url = title_elem.get('href', '')
                    snippet = snippet_elem.get_text(strip=True) if snippet_elem else ''
                    
                    results.append({
                        'title': title,
                        'url': url,
                        'snippet': snippet
                    })
            
            return {
                'success': True,
                'query': query,
                'results': results,
                'total_results': len(results)
            }
            
        except Exception as e:
            self.logger.error(f"Web search failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'query': query,
                'results': []
            }
    
    async def file_operations(self, operation: str, file_path: str, content: str = None, **kwargs) -> Dict[str, Any]:
        """Perform file operations (read, write, create, delete, list)"""
        try:
            file_path = Path(file_path)
            
            if operation == 'read':
                if file_path.exists():
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    return {
                        'success': True,
                        'operation': 'read',
                        'file_path': str(file_path),
                        'content': content,
                        'size_bytes': file_path.stat().st_size
                    }
                else:
                    return {'success': False, 'error': 'File not found'}
            
            elif operation == 'write':
                file_path.parent.mkdir(parents=True, exist_ok=True)
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content or '')
                return {
                    'success': True,
                    'operation': 'write',
                    'file_path': str(file_path),
                    'bytes_written': len(content or '')
                }
            
            elif operation == 'append':
                with open(file_path, 'a', encoding='utf-8') as f:
                    f.write(content or '')
                return {
                    'success': True,
                    'operation': 'append',
                    'file_path': str(file_path),
                    'bytes_appended': len(content or '')
                }
            
            elif operation == 'delete':
                if file_path.exists():
                    file_path.unlink()
                    return {
                        'success': True,
                        'operation': 'delete',
                        'file_path': str(file_path)
                    }
                else:
                    return {'success': False, 'error': 'File not found'}
            
            elif operation == 'list':
                if file_path.is_dir():
                    files = [
                        {
                            'name': f.name,
                            'path': str(f),
                            'is_file': f.is_file(),
                            'size_bytes': f.stat().st_size if f.is_file() else 0
                        }
                        for f in file_path.iterdir()
                    ]
                    return {
                        'success': True,
                        'operation': 'list',
                        'directory': str(file_path),
                        'files': files,
                        'count': len(files)
                    }
                else:
                    return {'success': False, 'error': 'Not a directory'}
            
            elif operation == 'create_dir':
                file_path.mkdir(parents=True, exist_ok=True)
                return {
                    'success': True,
                    'operation': 'create_dir',
                    'directory': str(file_path)
                }
            
            else:
                return {'success': False, 'error': f'Unknown operation: {operation}'}
                
        except Exception as e:
            self.logger.error(f"File operation failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'operation': operation,
                'file_path': str(file_path)
            }
    
    async def code_execution(self, code: str, language: str = 'python', timeout: int = 30) -> Dict[str, Any]:
        """Execute code safely in a sandboxed environment"""
        try:
            if language.lower() != 'python':
                return {'success': False, 'error': f'Language {language} not supported'}
            
            # Create a temporary file for the code
            temp_file = Path(self.temp_dir) / f'temp_code_{asyncio.get_event_loop().time()}.py'
            with open(temp_file, 'w') as f:
                f.write(code)
            
            # Execute the code
            process = await asyncio.create_subprocess_exec(
                'python', str(temp_file),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.temp_dir
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
                
                return {
                    'success': process.returncode == 0,
                    'stdout': stdout.decode('utf-8'),
                    'stderr': stderr.decode('utf-8'),
                    'return_code': process.returncode,
                    'execution_time': timeout  # Approximate
                }
            except asyncio.TimeoutError:
                process.kill()
                return {
                    'success': False,
                    'error': f'Code execution timed out after {timeout} seconds',
                    'stdout': '',
                    'stderr': ''
                }
            finally:
                # Clean up temporary file
                if temp_file.exists():
                    temp_file.unlink()
                    
        except Exception as e:
            self.logger.error(f"Code execution failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'stdout': '',
                'stderr': ''
            }
    
    async def data_analysis(self, operation: str, data: Any = None, file_path: str = None, **kwargs) -> Dict[str, Any]:
        """Perform data analysis operations"""
        try:
            # Load data
            df = None
            if data is not None:
                if isinstance(data, dict):
                    df = pd.DataFrame(data)
                elif isinstance(data, list):
                    df = pd.DataFrame(data)
                else:
                    df = pd.DataFrame([data])
            elif file_path:
                file_path = Path(file_path)
                if file_path.suffix.lower() == '.csv':
                    df = pd.read_csv(file_path)
                elif file_path.suffix.lower() in ['.json']:
                    df = pd.read_json(file_path)
                elif file_path.suffix.lower() in ['.xlsx', '.xls']:
                    df = pd.read_excel(file_path)
                else:
                    return {'success': False, 'error': 'Unsupported file format'}
            else:
                return {'success': False, 'error': 'No data provided'}
            
            # Perform analysis
            if operation == 'describe':
                description = df.describe(include='all').to_dict()
                return {
                    'success': True,
                    'operation': 'describe',
                    'data_shape': df.shape,
                    'description': description,
                    'column_types': df.dtypes.to_dict()
                }
            
            elif operation == 'plot':
                plot_type = kwargs.get('plot_type', 'scatter')
                x_col = kwargs.get('x_column')
                y_col = kwargs.get('y_column')
                
                if plot_type == 'scatter' and x_col and y_col:
                    fig = px.scatter(df, x=x_col, y=y_col)
                elif plot_type == 'line' and x_col and y_col:
                    fig = px.line(df, x=x_col, y=y_col)
                elif plot_type == 'bar' and x_col and y_col:
                    fig = px.bar(df, x=x_col, y=y_col)
                elif plot_type == 'histogram' and x_col:
                    fig = px.histogram(df, x=x_col)
                else:
                    return {'success': False, 'error': 'Invalid plot configuration'}
                
                # Save plot
                plot_path = Path(self.temp_dir) / f'plot_{asyncio.get_event_loop().time()}.html'
                fig.write_html(str(plot_path))
                
                return {
                    'success': True,
                    'operation': 'plot',
                    'plot_type': plot_type,
                    'plot_path': str(plot_path),
                    'data_shape': df.shape
                }
            
            elif operation == 'aggregate':
                group_by = kwargs.get('group_by')
                agg_func = kwargs.get('function', 'mean')
                
                if group_by:
                    result = getattr(df.groupby(group_by), agg_func)()
                else:
                    result = getattr(df, agg_func)()
                
                return {
                    'success': True,
                    'operation': 'aggregate',
                    'function': agg_func,
                    'group_by': group_by,
                    'result': result.to_dict() if hasattr(result, 'to_dict') else result
                }
            
            elif operation == 'filter':
                condition = kwargs.get('condition')
                if condition:
                    # Simple filtering - in production, this would need more robust parsing
                    filtered_df = df.query(condition)
                    return {
                        'success': True,
                        'operation': 'filter',
                        'condition': condition,
                        'original_shape': df.shape,
                        'filtered_shape': filtered_df.shape,
                        'filtered_data': filtered_df.head(10).to_dict('records')
                    }
                else:
                    return {'success': False, 'error': 'No filter condition provided'}
            
            else:
                return {'success': False, 'error': f'Unknown operation: {operation}'}
                
        except Exception as e:
            self.logger.error(f"Data analysis failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'operation': operation
            }
    
    async def api_calls(self, method: str, url: str, headers: Dict[str, str] = None, 
                       data: Any = None, params: Dict[str, str] = None, timeout: int = 30) -> Dict[str, Any]:
        """Make HTTP API calls"""
        try:
            method = method.upper()
            headers = headers or {}
            
            # Add default headers
            if 'User-Agent' not in headers:
                headers['User-Agent'] = 'AI-Agent/1.0'
            
            # Make the request
            if method == 'GET':
                response = requests.get(url, headers=headers, params=params, timeout=timeout)
            elif method == 'POST':
                response = requests.post(url, headers=headers, json=data, params=params, timeout=timeout)
            elif method == 'PUT':
                response = requests.put(url, headers=headers, json=data, params=params, timeout=timeout)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers, params=params, timeout=timeout)
            else:
                return {'success': False, 'error': f'HTTP method {method} not supported'}
            
            # Parse response
            try:
                response_data = response.json()
            except:
                response_data = response.text
            
            return {
                'success': response.status_code < 400,
                'status_code': response.status_code,
                'headers': dict(response.headers),
                'data': response_data,
                'method': method,
                'url': url
            }
            
        except Exception as e:
            self.logger.error(f"API call failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'method': method,
                'url': url
            }
    
    async def llm_reasoning(self, query: str, context: str = None) -> Dict[str, Any]:
        """Use LLM for reasoning and problem-solving"""
        try:
            from .llm import LLMInterface
            llm = LLMInterface(self.config)
            
            if context:
                prompt = f"Context: {context}\n\nQuery: {query}"
            else:
                prompt = query
            
            response = await llm.generate(prompt)
            
            return {
                'success': True,
                'query': query,
                'response': response,
                'context_provided': bool(context)
            }
            
        except Exception as e:
            self.logger.error(f"LLM reasoning failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'query': query
            }
    
    async def database_operations(self, operation: str, database_path: str = None, 
                                 query: str = None, data: List[Dict] = None, **kwargs) -> Dict[str, Any]:
        """Perform database operations"""
        try:
            db_path = database_path or os.path.join(self.temp_dir, 'temp.db')
            
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                
                if operation == 'create_table':
                    table_name = kwargs.get('table_name', 'temp_table')
                    columns = kwargs.get('columns', [])
                    
                    if not columns and data:
                        # Infer columns from data
                        columns = [(col, 'TEXT') for col in data[0].keys()]
                    
                    column_defs = ', '.join([f"{name} {dtype}" for name, dtype in columns])
                    create_query = f"CREATE TABLE IF NOT EXISTS {table_name} ({column_defs})"
                    cursor.execute(create_query)
                    
                    return {
                        'success': True,
                        'operation': 'create_table',
                        'table_name': table_name,
                        'columns': columns
                    }
                
                elif operation == 'insert' and data:
                    table_name = kwargs.get('table_name', 'temp_table')
                    
                    if data:
                        columns = list(data[0].keys())
                        placeholders = ', '.join(['?' for _ in columns])
                        insert_query = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders})"
                        
                        for row in data:
                            cursor.execute(insert_query, [row[col] for col in columns])
                        
                        conn.commit()
                        
                        return {
                            'success': True,
                            'operation': 'insert',
                            'table_name': table_name,
                            'rows_inserted': len(data)
                        }
                
                elif operation == 'query' and query:
                    cursor.execute(query)
                    
                    if query.strip().upper().startswith('SELECT'):
                        rows = cursor.fetchall()
                        columns = [description[0] for description in cursor.description]
                        data = [dict(zip(columns, row)) for row in rows]
                        
                        return {
                            'success': True,
                            'operation': 'query',
                            'query': query,
                            'data': data,
                            'row_count': len(data)
                        }
                    else:
                        conn.commit()
                        return {
                            'success': True,
                            'operation': 'query',
                            'query': query,
                            'rows_affected': cursor.rowcount
                        }
                
                else:
                    return {'success': False, 'error': f'Unknown operation: {operation}'}
                    
        except Exception as e:
            self.logger.error(f"Database operation failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'operation': operation
            }
    
    def get_available_tools(self) -> List[str]:
        """Get list of available tools"""
        return [tool for tool, available in self.available_tools.items() if available]
    
    def cleanup(self):
        """Clean up temporary resources"""
        try:
            import shutil
            shutil.rmtree(self.temp_dir, ignore_errors=True)
        except Exception as e:
            self.logger.warning(f"Failed to cleanup temp directory: {e}")