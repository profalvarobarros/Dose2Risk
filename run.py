import os
from dose2risk.api import create_app

if __name__ == '__main__':
    app = create_app()
    # Debug apenas se FLASK_ENV for 'development'
    is_debug = os.getenv('FLASK_ENV', 'production') == 'development'
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=is_debug)
