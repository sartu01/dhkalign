"""
Enhanced Logging System for DHK Align WRAITH
Comprehensive logging with structured output, performance tracking, and security considerations.
"""

import logging
import logging.handlers
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
from functools import wraps
import hashlib
import sys

# Configuration
LOG_DIR = Path("logs")
LOG_FORMAT = "%(asctime)s | %(name)s | %(levelname)s | %(message)s"
JSON_LOG_FORMAT = True  # Set to False for plain text logs

class StructuredFormatter(logging.Formatter):
    """Custom formatter for structured JSON logging"""
    
    def format(self, record):
        # Create structured log entry
        log_entry = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # Add extra fields if present
        if hasattr(record, 'extra_fields'):
            log_entry.update(record.extra_fields)
        
        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_entry, ensure_ascii=False)

class SecuritySafeFormatter(logging.Formatter):
    """Formatter that sanitizes sensitive information"""
    
    SENSITIVE_PATTERNS = [
        "password", "token", "key", "secret", "auth", "credential"
    ]
    
    def format(self, record):
        # Sanitize the message
        message = record.getMessage()
        
        # Hash or redact sensitive information
        for pattern in self.SENSITIVE_PATTERNS:
            if pattern.lower() in message.lower():
                # Replace with hash or redaction
                message = self._sanitize_message(message)
                break
        
        # Create sanitized record
        record.msg = message
        return super().format(record)
    
    def _sanitize_message(self, message: str) -> str:
        """Sanitize sensitive information in log messages"""
        # For demo, just indicate sanitization occurred
        return f"[SANITIZED] {message[:50]}..."

class TranslationLogger:
    """Specialized logger for translation operations"""
    
    def __init__(self, name: str = "dhk_align"):
        self.logger = logging.getLogger(name)
        self._setup_logging()
    
    def _setup_logging(self):
        """Setup comprehensive logging configuration"""
        # Create logs directory
        LOG_DIR.mkdir(exist_ok=True)
        
        # Clear existing handlers
        self.logger.handlers.clear()
        self.logger.setLevel(logging.DEBUG)
        
        # Console Handler (INFO and above)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        if JSON_LOG_FORMAT:
            console_handler.setFormatter(StructuredFormatter())
        else:
            console_handler.setFormatter(logging.Formatter(LOG_FORMAT))
        self.logger.addHandler(console_handler)
        
        # File Handler - General logs (rotating)
        file_handler = logging.handlers.RotatingFileHandler(
            LOG_DIR / "dhk_align.log",
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(SecuritySafeFormatter(LOG_FORMAT))
        self.logger.addHandler(file_handler)
        
        # File Handler - Translation operations (JSON)
        translation_handler = logging.handlers.RotatingFileHandler(
            LOG_DIR / "translations.jsonl",
            maxBytes=50*1024*1024,  # 50MB
            backupCount=10
        )
        translation_handler.setLevel(logging.INFO)
        translation_handler.setFormatter(StructuredFormatter())
        translation_handler.addFilter(TranslationFilter())
        self.logger.addHandler(translation_handler)
        
        # File Handler - Errors only
        error_handler = logging.handlers.RotatingFileHandler(
            LOG_DIR / "errors.log",
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(SecuritySafeFormatter(LOG_FORMAT))
        self.logger.addHandler(error_handler)
        
        # Performance Handler - Metrics and timing
        perf_handler = logging.handlers.RotatingFileHandler(
            LOG_DIR / "performance.jsonl",
            maxBytes=25*1024*1024,  # 25MB
            backupCount=5
        )
        perf_handler.setLevel(logging.INFO)
        perf_handler.setFormatter(StructuredFormatter())
        perf_handler.addFilter(PerformanceFilter())
        self.logger.addHandler(perf_handler)
    
    def info(self, message: str, **kwargs):
        """Log info message with optional extra fields"""
        self.logger.info(message, extra={'extra_fields': kwargs})
    
    def error(self, message: str, **kwargs):
        """Log error message with optional extra fields"""
        self.logger.error(message, extra={'extra_fields': kwargs})
    
    def debug(self, message: str, **kwargs):
        """Log debug message with optional extra fields"""
        self.logger.debug(message, extra={'extra_fields': kwargs})
    
    def warning(self, message: str, **kwargs):
        """Log warning message with optional extra fields"""
        self.logger.warning(message, extra={'extra_fields': kwargs})
    
    def translation_request(self, query: str, direction: str, user_session: str = None):
        """Log translation request"""
        self.logger.info("Translation request received", extra={
            'extra_fields': {
                'event_type': 'translation_request',
                'query_hash': hashlib.sha256(query.encode()).hexdigest()[:16],
                'query_length': len(query),
                'direction': direction,
                'user_session': user_session,
                'timestamp': datetime.now().isoformat()
            }
        })
    
    def translation_result(self, query: str, result: Dict[str, Any], processing_time_ms: float):
        """Log translation result with performance metrics"""
        self.logger.info("Translation completed", extra={
            'extra_fields': {
                'event_type': 'translation_result',
                'query_hash': hashlib.sha256(query.encode()).hexdigest()[:16],
                'success': result.get('success', False),
                'method': result.get('method', 'unknown'),
                'confidence': result.get('confidence', 0),
                'processing_time_ms': processing_time_ms,
                'enhancement_used': result.get('method') != 'exact',
                'timestamp': datetime.now().isoformat()
            }
        })
    
    def translation_miss(self, query: str, direction: str, user_session: str = None):
        """Log translation miss for dataset improvement"""
        self.logger.warning("Translation miss", extra={
            'extra_fields': {
                'event_type': 'translation_miss',
                'query_hash': hashlib.sha256(query.encode()).hexdigest()[:16],
                'query_length': len(query),
                'direction': direction,
                'user_session': user_session,
                'priority': 'dataset_expansion',
                'timestamp': datetime.now().isoformat()
            }
        })
    
    def user_feedback(self, query: str, feedback_type: str, is_positive: bool):
        """Log user feedback for learning"""
        self.logger.info("User feedback received", extra={
            'extra_fields': {
                'event_type': 'user_feedback',
                'query_hash': hashlib.sha256(query.encode()).hexdigest()[:16],
                'feedback_type': feedback_type,
                'is_positive': is_positive,
                'learning_signal': 'strong' if is_positive else 'correction',
                'timestamp': datetime.now().isoformat()
            }
        })
    
    def performance_metric(self, operation: str, duration_ms: float, **metrics):
        """Log performance metrics"""
        self.logger.info(f"Performance metric: {operation}", extra={
            'extra_fields': {
                'event_type': 'performance_metric',
                'operation': operation,
                'duration_ms': duration_ms,
                'timestamp': datetime.now().isoformat(),
                **metrics
            }
        })
    
    def database_operation(self, operation: str, success: bool, duration_ms: float = None, **details):
        """Log database operations"""
        level = logging.INFO if success else logging.ERROR
        self.logger.log(level, f"Database operation: {operation}", extra={
            'extra_fields': {
                'event_type': 'database_operation',
                'operation': operation,
                'success': success,
                'duration_ms': duration_ms,
                'timestamp': datetime.now().isoformat(),
                **details
            }
        })
    
    def security_event(self, event_type: str, details: Dict[str, Any], severity: str = "warning"):
        """Log security-related events"""
        level = getattr(logging, severity.upper(), logging.WARNING)
        self.logger.log(level, f"Security event: {event_type}", extra={
            'extra_fields': {
                'event_type': 'security_event',
                'security_event_type': event_type,
                'severity': severity,
                'timestamp': datetime.now().isoformat(),
                **details
            }
        })

class TranslationFilter(logging.Filter):
    """Filter to only log translation-related events"""
    
    def filter(self, record):
        return hasattr(record, 'extra_fields') and \
               record.extra_fields.get('event_type', '').startswith('translation')

class PerformanceFilter(logging.Filter):
    """Filter to only log performance-related events"""
    
    def filter(self, record):
        return hasattr(record, 'extra_fields') and \
               record.extra_fields.get('event_type') in ['performance_metric', 'translation_result']

def log_execution_time(logger: TranslationLogger, operation_name: str):
    """Decorator to log function execution time"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000
                logger.performance_metric(
                    operation=operation_name,
                    duration_ms=duration_ms,
                    success=True,
                    function=func.__name__
                )
                return result
            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                logger.error(f"Error in {operation_name}: {str(e)}", 
                           operation=operation_name, 
                           duration_ms=duration_ms,
                           function=func.__name__,
                           error_type=type(e).__name__)
                raise
        return wrapper
    return decorator

def log_api_request(logger: TranslationLogger):
    """Decorator to log API requests"""
    def decorator(func):
        @wraps(func)
        async def wrapper(request, *args, **kwargs):
            start_time = time.time()
            client_ip = getattr(request.client, 'host', 'unknown')
            user_agent = request.headers.get('user-agent', 'unknown')
            
            # Create session hash for privacy
            session_hash = hashlib.sha256(f"{client_ip}:{user_agent}".encode()).hexdigest()[:16]
            
            logger.info(f"API request: {func.__name__}", 
                       endpoint=func.__name__,
                       client_session=session_hash,
                       user_agent=user_agent[:100])  # Truncate long user agents
            
            try:
                result = await func(request, *args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000
                
                # Log successful request
                logger.performance_metric(
                    operation=f"api_{func.__name__}",
                    duration_ms=duration_ms,
                    success=True,
                    client_session=session_hash
                )
                
                return result
            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                logger.error(f"API error in {func.__name__}: {str(e)}",
                           endpoint=func.__name__,
                           duration_ms=duration_ms,
                           client_session=session_hash,
                           error_type=type(e).__name__)
                raise
        return wrapper
    return decorator

class LogAnalyzer:
    """Utility class for analyzing logs"""
    
    def __init__(self, log_dir: Path = LOG_DIR):
        self.log_dir = log_dir
    
    def get_translation_stats(self, hours: int = 24) -> Dict[str, Any]:
        """Analyze translation logs for the past N hours"""
        stats = {
            'total_requests': 0,
            'successful_translations': 0,
            'translation_misses': 0,
            'methods_used': {},
            'avg_processing_time_ms': 0,
            'user_feedback_count': 0
        }
        
        try:
            log_file = self.log_dir / "translations.jsonl"
            if not log_file.exists():
                return stats
            
            cutoff_time = datetime.now().timestamp() - (hours * 3600)
            processing_times = []
            
            with open(log_file, 'r') as f:
                for line in f:
                    try:
                        entry = json.loads(line)
                        if entry['timestamp'] < cutoff_time:
                            continue
                        
                        event_type = entry.get('event_type')
                        
                        if event_type == 'translation_request':
                            stats['total_requests'] += 1
                        elif event_type == 'translation_result':
                            if entry.get('success'):
                                stats['successful_translations'] += 1
                                method = entry.get('method', 'unknown')
                                stats['methods_used'][method] = stats['methods_used'].get(method, 0) + 1
                                
                                if 'processing_time_ms' in entry:
                                    processing_times.append(entry['processing_time_ms'])
                        elif event_type == 'translation_miss':
                            stats['translation_misses'] += 1
                        elif event_type == 'user_feedback':
                            stats['user_feedback_count'] += 1
                    
                    except (json.JSONDecodeError, KeyError):
                        continue
            
            if processing_times:
                stats['avg_processing_time_ms'] = sum(processing_times) / len(processing_times)
        
        except Exception as e:
            print(f"Error analyzing logs: {e}")
        
        return stats
    
    def get_error_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get summary of errors from the past N hours"""
        error_summary = {
            'total_errors': 0,
            'error_types': {},
            'critical_errors': 0
        }
        
        try:
            log_file = self.log_dir / "errors.log"
            if not log_file.exists():
                return error_summary
            
            cutoff_time = datetime.now().timestamp() - (hours * 3600)
            
            with open(log_file, 'r') as f:
                for line in f:
                    if 'ERROR' in line:
                        error_summary['total_errors'] += 1
                        # Simple error type extraction
                        if 'Database' in line:
                            error_summary['error_types']['database'] = error_summary['error_types'].get('database', 0) + 1
                        elif 'Translation' in line:
                            error_summary['error_types']['translation'] = error_summary['error_types'].get('translation', 0) + 1
                        else:
                            error_summary['error_types']['other'] = error_summary['error_types'].get('other', 0) + 1
        
        except Exception as e:
            print(f"Error analyzing error logs: {e}")
        
        return error_summary

# Global logger instance
logger = TranslationLogger()

# Convenience functions for common logging patterns
def log_startup(message: str, **details):
    """Log application startup events"""
    logger.info(f"🚀 STARTUP: {message}", event_type='startup', **details)

def log_shutdown(message: str, **details):
    """Log application shutdown events"""
    logger.info(f"👋 SHUTDOWN: {message}", event_type='shutdown', **details)

def log_config_change(component: str, old_value: Any, new_value: Any):
    """Log configuration changes"""
    logger.info(f"Configuration changed: {component}", 
               event_type='config_change',
               component=component,
               old_value=str(old_value),
               new_value=str(new_value))

def log_health_check(status: str, **metrics):
    """Log health check results"""
    level = logging.INFO if status == 'healthy' else logging.WARNING
    logger.logger.log(level, f"Health check: {status}",
                     extra={'extra_fields': {'event_type': 'health_check', 'status': status, **metrics}})

# Export main components
__all__ = [
    'TranslationLogger',
    'logger',
    'log_execution_time',
    'log_api_request', 
    'LogAnalyzer',
    'log_startup',
    'log_shutdown',
    'log_config_change',
    'log_health_check'
]