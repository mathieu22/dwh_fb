"""
API Uploads - Gestion des fichiers uploadés (images)
"""
from flask import request, jsonify, current_app, send_from_directory
from flask_jwt_extended import jwt_required
from werkzeug.exceptions import RequestEntityTooLarge

from . import api_v1
from app.services.upload_service import UploadService
from app.core.security import role_required, UserRoles


@api_v1.route('/uploads/images', methods=['POST'])
@jwt_required()
@role_required([UserRoles.ADMIN, UserRoles.CONTROLEUR])
def upload_image():
    """
    Upload une image pour un produit ou une catégorie.
    ---
    tags:
      - Uploads
    summary: Upload d'image
    description: |
      Upload une image avec redimensionnement automatique.
      Formats acceptés: PNG, JPG, JPEG, GIF, WEBP
      Taille max: 5MB
      L'image est automatiquement redimensionnée si elle dépasse 800x800px.
      Une miniature 200x200px est également générée.
    security:
      - Bearer: []
    consumes:
      - multipart/form-data
    parameters:
      - name: file
        in: formData
        type: file
        required: true
        description: Fichier image à uploader
      - name: type
        in: formData
        type: string
        enum: [products, categories]
        default: products
        description: Type de ressource (détermine le sous-dossier)
    responses:
      201:
        description: Image uploadée avec succès
        schema:
          type: object
          properties:
            success:
              type: boolean
            message:
              type: string
            data:
              type: object
              properties:
                original_filename:
                  type: string
                filename:
                  type: string
                url:
                  type: string
                thumbnail_url:
                  type: string
                size:
                  type: integer
      400:
        description: Erreur de validation
      413:
        description: Fichier trop volumineux
    """
    # Vérifier qu'un fichier est présent
    if 'file' not in request.files:
        return jsonify({
            'success': False,
            'error': 'Aucun fichier fourni',
            'message': "Le champ 'file' est requis"
        }), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({
            'success': False,
            'error': 'Fichier vide',
            'message': 'Veuillez sélectionner un fichier'
        }), 400

    # Récupérer le type (products ou categories)
    upload_type = request.form.get('type', 'products')
    if upload_type not in ['products', 'categories']:
        upload_type = 'products'

    try:
        # Utiliser le service d'upload
        result = UploadService.save_image(file, subfolder=upload_type)

        return jsonify({
            'success': True,
            'message': 'Image uploadée avec succès',
            'data': result
        }), 201

    except ValueError as e:
        return jsonify({
            'success': False,
            'error': 'Validation error',
            'message': str(e)
        }), 400
    except Exception as e:
        current_app.logger.error(f"Erreur upload image: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Server error',
            'message': "Erreur lors de l'upload de l'image"
        }), 500


@api_v1.route('/uploads/images/multiple', methods=['POST'])
@jwt_required()
@role_required([UserRoles.ADMIN, UserRoles.CONTROLEUR])
def upload_multiple_images():
    """
    Upload plusieurs images en une seule requête.
    ---
    tags:
      - Uploads
    summary: Upload multiple d'images
    description: |
      Upload plusieurs images simultanément.
      Maximum 10 fichiers par requête.
    security:
      - Bearer: []
    consumes:
      - multipart/form-data
    parameters:
      - name: files
        in: formData
        type: file
        required: true
        description: Fichiers images à uploader (multiple)
      - name: type
        in: formData
        type: string
        enum: [products, categories]
        default: products
    responses:
      201:
        description: Images uploadées avec succès
      400:
        description: Erreur de validation
    """
    if 'files' not in request.files:
        return jsonify({
            'success': False,
            'error': 'Aucun fichier fourni',
            'message': "Le champ 'files' est requis"
        }), 400

    files = request.files.getlist('files')

    if len(files) == 0:
        return jsonify({
            'success': False,
            'error': 'Aucun fichier',
            'message': 'Veuillez sélectionner au moins un fichier'
        }), 400

    if len(files) > 10:
        return jsonify({
            'success': False,
            'error': 'Trop de fichiers',
            'message': 'Maximum 10 fichiers par requête'
        }), 400

    upload_type = request.form.get('type', 'products')
    if upload_type not in ['products', 'categories']:
        upload_type = 'products'

    results = []
    errors = []

    for file in files:
        if file.filename == '':
            continue

        try:
            result = UploadService.save_image(file, subfolder=upload_type)
            results.append(result)
        except ValueError as e:
            errors.append({
                'filename': file.filename,
                'error': str(e)
            })
        except Exception as e:
            errors.append({
                'filename': file.filename,
                'error': "Erreur lors de l'upload"
            })

    return jsonify({
        'success': len(results) > 0,
        'message': f'{len(results)} image(s) uploadée(s), {len(errors)} erreur(s)',
        'data': {
            'uploaded': results,
            'errors': errors
        }
    }), 201 if len(results) > 0 else 400


@api_v1.route('/uploads/images/<path:filepath>', methods=['DELETE'])
@jwt_required()
@role_required([UserRoles.ADMIN, UserRoles.CONTROLEUR])
def delete_image(filepath):
    """
    Supprime une image uploadée.
    ---
    tags:
      - Uploads
    summary: Supprimer une image
    security:
      - Bearer: []
    parameters:
      - name: filepath
        in: path
        type: string
        required: true
        description: Chemin relatif du fichier (ex: products/img_xxx.jpg)
    responses:
      200:
        description: Image supprimée avec succès
      404:
        description: Image non trouvée
    """
    try:
        deleted = UploadService.delete_image(filepath)

        if deleted:
            return jsonify({
                'success': True,
                'message': 'Image supprimée avec succès'
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': 'Not found',
                'message': 'Image non trouvée'
            }), 404

    except Exception as e:
        current_app.logger.error(f"Erreur suppression image: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Server error',
            'message': "Erreur lors de la suppression"
        }), 500


# Gestionnaire d'erreur pour fichiers trop volumineux
@api_v1.errorhandler(RequestEntityTooLarge)
def handle_file_too_large(e):
    max_size = current_app.config.get('MAX_CONTENT_LENGTH', 5 * 1024 * 1024)
    max_size_mb = max_size / (1024 * 1024)
    return jsonify({
        'success': False,
        'error': 'File too large',
        'message': f'Le fichier dépasse la taille maximale autorisée ({max_size_mb}MB)'
    }), 413
