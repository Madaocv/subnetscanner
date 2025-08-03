# app/run_scan.py
import asyncio
import datetime
import logging
import subprocess
import json
import tempfile
import os
from pathlib import Path
from sqlalchemy.orm import Session
from . import crud, models

async def run_scan(site_id: int, execution_id: int, logger=None):
    """
    Run scan as a background task using site_id instead of site object
    
    Args:
        site_id: ID сайту для сканування
        execution_id: ID виконання
        logger: Логер для запису подій (опціонально)
    """
    # Якщо логер не передано, створюємо локальний
    if logger is None:
        logger = logging.getLogger(__name__)
    logger.info(f"[BACKGROUND TASK] Starting run_scan for site_id={site_id}, execution_id={execution_id}")
    
    # Create a new DB session inside the background task
    from .database import SessionLocal
    db = SessionLocal()
    try:
        # Get the site object within this session
        site = db.query(models.Site).filter(models.Site.id == site_id).first()
        if not site:
            logger.error(f"Site {site_id} not found")
            crud.update_execution_status(db, execution_id=execution_id, status="failed", data={"error": "Site not found"})
            return
            
        logger.info(f"Starting scan for site {site.name} (ID: {site.id}), execution ID: {execution_id}")
        
        # Update status to running immediately
        crud.update_execution_status(db, execution_id=execution_id, status="running")
        logger.info(f"Updated execution {execution_id} status to 'running'")
        # Отримуємо конфігурацію сайту для сканування
        site_config = crud.generate_run_config(db, site_id)
        from pprint import pformat
        config_str = pformat(site_config)
        logger.info(pformat(config_str))
        
        # Логуємо конфігурацію сайту
        logger.info(f"Site configuration for {site.name}:\n{config_str}")
        
        # Створюємо тимчасовий файл конфігурації
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_config:
            json.dump(site_config, temp_config, indent=2)
            temp_config_path = temp_config.name
            
        logger.info(f"Created temporary config file: {temp_config_path}")
        
        try:
            # Шлях до кореневої директорії проекту
            project_root = Path(__file__).parent.parent
            site_scanner_path = project_root / "site_scanner.py"
            
            # В Docker використовуємо системний Python, локально - venv
            venv_python_path = project_root / ".venv" / "bin" / "python"
            if venv_python_path.exists():
                python_executable = str(venv_python_path)
            else:
                python_executable = "python3"  # Системний Python в Docker
            
            logger.info(f"Running site scanner: {python_executable} {site_scanner_path} {temp_config_path}")
            
            # Запускаємо site_scanner.py
            result = await asyncio.create_subprocess_exec(
                python_executable,
                str(site_scanner_path),
                temp_config_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(project_root)
            )
            
            stdout, stderr = await result.communicate()
            
            # Декодуємо результати
            stdout_text = stdout.decode('utf-8') if stdout else ""
            stderr_text = stderr.decode('utf-8') if stderr else ""
            
            logger.info(f"Site scanner exit code: {result.returncode}")
            if stdout_text:
                logger.info(f"Site scanner stdout:\n{stdout_text}")
            if stderr_text:
                logger.warning(f"Site scanner stderr:\n{stderr_text}")
            
            # Обробляємо результат
            execution = crud.get_execution(db, execution_id)
            if execution:
                if result.returncode == 0:
                    # Успішне виконання
                    scan_result = {
                        "scan_completed": True,
                        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                        "exit_code": result.returncode,
                        "stdout": stdout_text,
                        "stderr": stderr_text,
                        "config_file": temp_config_path
                    }
                    
                    # Спробуємо знайти JSON результат у stdout
                    try:
                        # Якщо stdout містить JSON, спробуємо його парсити
                        if stdout_text.strip():
                            lines = stdout_text.strip().split('\n')
                            for line in lines:
                                if line.strip().startswith('{') and line.strip().endswith('}'):
                                    json_result = json.loads(line.strip())
                                    scan_result["parsed_result"] = json_result
                                    break
                    except json.JSONDecodeError:
                        logger.warning("Could not parse JSON from site scanner output")
                    
                    crud.update_execution_status(
                        db, 
                        execution_id=execution_id, 
                        status="completed", 
                        data=scan_result
                    )
                    logger.info(f"Site scan completed successfully for execution ID: {execution_id}")
                else:
                    # Помилка виконання
                    error_result = {
                        "scan_completed": False,
                        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                        "exit_code": result.returncode,
                        "error": f"Site scanner failed with exit code {result.returncode}",
                        "stdout": stdout_text,
                        "stderr": stderr_text
                    }
                    crud.update_execution_status(
                        db, 
                        execution_id=execution_id, 
                        status="failed", 
                        data=error_result
                    )
                    logger.error(f"Site scan failed for execution ID: {execution_id}, exit code: {result.returncode}")
        
        finally:
            # Видаляємо тимчасовий файл
            try:
                os.unlink(temp_config_path)
                logger.info(f"Cleaned up temporary config file: {temp_config_path}")
            except Exception as cleanup_error:
                logger.warning(f"Failed to cleanup temp file {temp_config_path}: {cleanup_error}")
            
    except Exception as e:
        logger.error(f"Exception in run_scan: {str(e)}", exc_info=True)
        logger.info(f"[ERROR] Exception in run_scan: {str(e)}")
        try:
            # Try to update execution status to failed
            crud.update_execution_status(db, execution_id=execution_id, status="failed", data={"error": str(e)})
        except Exception as update_error:
            logger.error(f"Failed to update execution status: {str(update_error)}")
            logger.info(f"[ERROR] Failed to update execution status: {str(update_error)}")
    finally:
        db.close()
        logger.info(f"[BACKGROUND TASK] Finished run_scan for execution_id={execution_id}")
        logger.info(f"[BACKGROUND TASK] Finished run_scan for execution_id={execution_id}")