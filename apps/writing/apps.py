from django.apps import AppConfig


class WritingConfig(AppConfig):
    name = "apps.writing"
    verbose_name = "Sitelen Pona Writing Practice"

    def ready(self):
        """
        Initialize app services when Django starts.

        This method is called by Django when the app is ready.
        We use it to initialize our services.
        """
        try:
            # Import services and initialize them if needed

            # Only initialize character recognition on demand to avoid
            # loading the ML model unnecessarily on startup

            # Log that services are initialized
            import logging

            logger = logging.getLogger(__name__)
            logger.info("Writing app services initialized")
        except Exception as e:
            import logging

            logger = logging.getLogger(__name__)
            logger.error(f"Error initializing Writing app services: {e}")
