@echo off

rem Check if "venv" directory exists
if not exist venv (

    echo Virtual environment does not exist.
    echo Creating virtual environment...
    echo -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
    
    python -m venv venv
    call venv\Scripts\activate || goto :error
    
    if not exist venv (
        echo Failed to create virtual environment
        goto :error
    )

    echo Installing dependencies...
    pip install -r requirements.txt
    
)

call venv\Scripts\activate || goto :error

rem Rest of script...

python main.py

goto :EOF

:error 
echo Failed to activate virtual environment