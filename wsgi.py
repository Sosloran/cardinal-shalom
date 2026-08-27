"""
Werkzeug middleware para servir archivos estáticos en producción
con whitenoise. Se activa automáticamente si whitenoise está instalado.
"""
import os
from database import _engine

# Configuración para producción
if os.environ.get("FLASK_ENV") == "production":
    from werkzeug.middleware.dispatcher import DispatcherMiddleware
    from werkzeug.serving import run_simple

    def make_wsgi_app():
        from app import app as flask_app
        from whitenoise import WhiteNoise
        
        # Whitenoise para archivos estáticos
        wsgi_app = DispatcherMiddleware(flask_app.wsgi_app, {
            '/static': WhiteNoise(flask_app.wsgi_app, root=os.path.join(os.path.dirname(__file__), 'static'))
        })
        return wsgi_app
    
    if __name__ == "__main__":
        wsgi_app = make_wsgi_app()
        run_simple('0.0.0.0', int(os.environ.get('PORT', 5000)), wsgi_app, use_reloader=False, use_debugger=False)
else:
    # Desarrollo local
    from app import app as application
