import os
from src.mcli.lib.logger.logger import (
    get_logger, enable_runtime_tracing, disable_runtime_tracing,
    enable_system_tracing, disable_system_tracing
)

def main():
    logger = get_logger()
    
    # Enable runtime tracing if environment variable is set
    trace_level = os.environ.get('MCLI_TRACE_LEVEL')
    if trace_level:
        try:
            # Convert to integer (1=function calls, 2=line by line, 3=verbose)
            level = int(trace_level)
            enable_runtime_tracing(level=level)
            logger.info(f"Runtime tracing enabled with level {level}")
        except ValueError:
            logger.warning(f"Invalid MCLI_TRACE_LEVEL value: {trace_level}. Using default level 1.")
            enable_runtime_tracing(level=1)
    
    # Enable system tracing if environment variable is set
    system_trace_level = os.environ.get('MCLI_SYSTEM_TRACE_LEVEL')
    system_trace_interval = os.environ.get('MCLI_SYSTEM_TRACE_INTERVAL')
    
    if system_trace_level:
        try:
            # Convert to integer (1=basic, 2=detailed)
            level = int(system_trace_level)
            
            # Get interval if specified
            interval = 5  # Default to 5 seconds
            if system_trace_interval:
                try:
                    interval = max(1, int(system_trace_interval))  # Minimum 1 second
                except ValueError:
                    logger.warning(f"Invalid MCLI_SYSTEM_TRACE_INTERVAL value: {system_trace_interval}. Using default interval 5s.")
                    
            enable_system_tracing(level=level, interval=interval)
            logger.info(f"System process tracing enabled with level {level}, interval {interval}s")
        except ValueError:
            logger.warning(f"Invalid MCLI_SYSTEM_TRACE_LEVEL value: {system_trace_level}. Using default level 1.")
            enable_system_tracing(level=1)
    
    try:
        logger.info("Hello from mcli!")
        # Import the app module here to use the full functionality
        from src.mcli.app.main import main as app_main
        app_main()
    except Exception as e:
        logger.error(f"Error in main function: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
    finally:
        # Make sure tracing is disabled on exit
        if trace_level:
            logger.debug("Disabling runtime tracing on exit")
            disable_runtime_tracing()
            
        if system_trace_level:
            logger.debug("Disabling system tracing on exit")
            disable_system_tracing()


if __name__ == "__main__":
    main()
