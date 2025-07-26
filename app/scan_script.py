async def run_scan(site_id: int, execution_id: int):
    """
    Run scan as a background task using site_id instead of site object
    """
    # Create a new DB session inside the background task
    from .database import SessionLocal
    db = SessionLocal()
    try:
        # Get the site object within this session
        site = db.query(models.Site).filter(models.Site.id == site_id).first()
        if not site:
            print(f"Site {site_id} not found")
            return
            
        print(f"Starting scan for site {site.name} (ID: {site.id}), execution ID: {execution_id}")
        await asyncio.sleep(120)  # Sleep for 2 minutes
        
        # Update the execution record
        execution = crud.get_execution(db, execution_id)
        if execution:
            # Update with mock data
            mock_data = {
                "scan_completed": True,
                "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "discovered_devices": [
                    {"ip": "192.168.1.1", "hostname": "router", "status": "up"},
                    {"ip": "192.168.1.10", "hostname": "server", "status": "up"},
                    {"ip": "192.168.1.20", "hostname": "workstation", "status": "up"}
                ]
            }
            # Update the execution record
            crud.update_execution_status(
                db, 
                execution_id=execution_id, 
                status="completed", 
                data=mock_data
            )
            print(f"Scan completed for execution ID: {execution_id}")
    finally:
        db.close()