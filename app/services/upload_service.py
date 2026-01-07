"""
Service d'upload et gestion des images
"""
import os
import uuid
from datetime import datetime
from werkzeug.utils import secure_filename
from PIL import Image
from flask import current_app


class UploadService:
    """Service pour gérer l'upload et le traitement des images"""

    @staticmethod
    def allowed_file(filename):
        """Vérifie si l'extension du fichier est autorisée"""
        if '.' not in filename:
            return False
        ext = filename.rsplit('.', 1)[1].lower()
        return ext in current_app.config['ALLOWED_IMAGE_EXTENSIONS']

    @staticmethod
    def get_extension(filename):
        """Récupère l'extension d'un fichier"""
        return filename.rsplit('.', 1)[1].lower() if '.' in filename else ''

    @staticmethod
    def generate_unique_filename(original_filename, prefix='img'):
        """Génère un nom de fichier unique"""
        ext = UploadService.get_extension(original_filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        unique_id = uuid.uuid4().hex[:8]
        return f"{prefix}_{timestamp}_{unique_id}.{ext}"

    @staticmethod
    def ensure_upload_folder(subfolder='products'):
        """Crée le dossier d'upload s'il n'existe pas"""
        upload_path = os.path.join(current_app.config['UPLOAD_FOLDER'], subfolder)
        if not os.path.exists(upload_path):
            os.makedirs(upload_path)
        return upload_path

    @staticmethod
    def resize_image(image, max_size):
        """Redimensionne une image en conservant le ratio"""
        image.thumbnail(max_size, Image.Resampling.LANCZOS)
        return image

    @staticmethod
    def save_image(file, subfolder='products', create_thumbnail=True):
        """
        Sauvegarde une image uploadée avec redimensionnement optionnel

        Args:
            file: FileStorage object from request.files
            subfolder: Sous-dossier de destination (products, categories, etc.)
            create_thumbnail: Créer une miniature ou non

        Returns:
            dict: Informations sur les fichiers sauvegardés
                - original_filename: nom original
                - filename: nouveau nom du fichier
                - filepath: chemin relatif du fichier
                - url: URL pour accéder au fichier
                - thumbnail_url: URL de la miniature (si créée)
                - size: taille en bytes
        """
        if not file or file.filename == '':
            raise ValueError("Aucun fichier fourni")

        original_filename = secure_filename(file.filename)

        if not UploadService.allowed_file(original_filename):
            allowed = ', '.join(current_app.config['ALLOWED_IMAGE_EXTENSIONS'])
            raise ValueError(f"Type de fichier non autorisé. Extensions acceptées: {allowed}")

        # Générer un nom unique
        new_filename = UploadService.generate_unique_filename(original_filename)

        # Créer le dossier si nécessaire
        upload_path = UploadService.ensure_upload_folder(subfolder)

        # Chemin complet du fichier
        filepath = os.path.join(upload_path, new_filename)

        # Ouvrir et traiter l'image avec Pillow
        image = Image.open(file.stream)

        # Convertir en RGB si nécessaire (pour les PNG avec transparence)
        if image.mode in ('RGBA', 'LA', 'P'):
            background = Image.new('RGB', image.size, (255, 255, 255))
            if image.mode == 'P':
                image = image.convert('RGBA')
            background.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
            image = background

        # Redimensionner si trop grande
        max_size = current_app.config.get('MAX_IMAGE_SIZE', (800, 800))
        if image.size[0] > max_size[0] or image.size[1] > max_size[1]:
            image = UploadService.resize_image(image, max_size)

        # Sauvegarder l'image principale
        image.save(filepath, quality=85, optimize=True)

        # Calculer la taille du fichier
        file_size = os.path.getsize(filepath)

        # Construire les URLs complètes avec la base URL
        base_url = current_app.config.get('UPLOAD_BASE_URL', 'http://localhost:5000')

        result = {
            'original_filename': original_filename,
            'filename': new_filename,
            'filepath': f"{subfolder}/{new_filename}",
            'url': f"{base_url}/uploads/{subfolder}/{new_filename}",
            'size': file_size
        }

        # Créer une miniature si demandé
        if create_thumbnail:
            thumb_filename = f"thumb_{new_filename}"
            thumb_path = os.path.join(upload_path, thumb_filename)

            thumbnail = image.copy()
            thumb_size = current_app.config.get('THUMBNAIL_SIZE', (200, 200))
            thumbnail.thumbnail(thumb_size, Image.Resampling.LANCZOS)
            thumbnail.save(thumb_path, quality=80, optimize=True)

            result['thumbnail_filename'] = thumb_filename
            result['thumbnail_url'] = f"{base_url}/uploads/{subfolder}/{thumb_filename}"

        return result

    @staticmethod
    def delete_image(filepath):
        """
        Supprime une image et sa miniature associée

        Args:
            filepath: Chemin relatif du fichier (ex: products/img_xxx.jpg)

        Returns:
            bool: True si supprimé, False sinon
        """
        if not filepath:
            return False

        full_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filepath)

        deleted = False

        # Supprimer le fichier principal
        if os.path.exists(full_path):
            os.remove(full_path)
            deleted = True

        # Supprimer la miniature si elle existe
        directory = os.path.dirname(full_path)
        filename = os.path.basename(full_path)
        thumb_path = os.path.join(directory, f"thumb_{filename}")

        if os.path.exists(thumb_path):
            os.remove(thumb_path)

        return deleted

    @staticmethod
    def get_image_info(filepath):
        """
        Récupère les informations d'une image

        Args:
            filepath: Chemin relatif du fichier

        Returns:
            dict: Informations sur l'image (dimensions, taille, etc.)
        """
        full_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filepath)

        if not os.path.exists(full_path):
            return None

        with Image.open(full_path) as img:
            return {
                'filepath': filepath,
                'width': img.size[0],
                'height': img.size[1],
                'format': img.format,
                'mode': img.mode,
                'size': os.path.getsize(full_path)
            }
