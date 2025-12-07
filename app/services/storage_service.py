
import os
import boto3
from botocore.exceptions import ClientError
from werkzeug.utils import secure_filename
import uuid
from datetime import datetime

class StorageService:
    def __init__(self):
        self.s3_client = None
        self.bucket_name = os.environ.get('R2_BUCKET_NAME')
        self.account_id = os.environ.get('R2_ACCOUNT_ID')
        self.access_key = os.environ.get('R2_ACCESS_KEY_ID')
        self.secret_key = os.environ.get('R2_SECRET_ACCESS_KEY')
        self.public_domain = os.environ.get('R2_PUBLIC_DOMAIN')

        if all([self.bucket_name, self.account_id, self.access_key, self.secret_key]):
            try:
                self.s3_client = boto3.client(
                    's3',
                    endpoint_url=f'https://{self.account_id}.r2.cloudflarestorage.com',
                    aws_access_key_id=self.access_key,
                    aws_secret_access_key=self.secret_key,
                    region_name='auto' # R2 requires a region, 'auto' is usually fine or 'us-east-1'
                )
            except Exception as e:
                print(f"Failed to initialize R2 client: {e}")

    def upload_file(self, file_obj, folder='photos'):
        """
        Uploads a file-like object to R2.
        Returns the public URL or the key if no public domain is set.
        """
        if not self.s3_client:
            print("R2 client not initialized. Check environment variables.")
            return None

        # Generate a unique filename
        original_filename = secure_filename(file_obj.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        unique_id = str(uuid.uuid4())[:8]
        extension = os.path.splitext(original_filename)[1]
        
        new_filename = f"{timestamp}_{unique_id}{extension}"
        key = f"{folder}/{new_filename}"

        try:
            # Upload the file
            # We reset the file pointer just in case
            file_obj.seek(0)
            self.s3_client.upload_fileobj(
                file_obj,
                self.bucket_name,
                key,
                ExtraArgs={'ContentType': file_obj.content_type}
            )

            # Return the URL
            if self.public_domain:
                # If using a custom domain or R2.dev subdomain
                return f"{self.public_domain.rstrip('/')}/{key}"
            else:
                # Fallback to signed URL or just return the key if we can't generate a public link easily
                # For now, let's return the key so the frontend knows it succeeded, 
                # but in a real app we might want a signed URL for private buckets.
                # Assuming public read access for the bucket for now.
                return key

        except ClientError as e:
            print(f"Error uploading file to R2: {e}")
            return None

    def delete_file(self, file_url):
        """
        Deletes a file from R2 given its URL or key.
        """
        if not self.s3_client:
            print("R2 client not initialized.")
            return False

        try:
            # Extract key from URL if needed
            key = file_url
            if self.public_domain and file_url.startswith(self.public_domain):
                key = file_url.replace(f"{self.public_domain.rstrip('/')}/", "")
            
            # Also handle if it's a full URL but not matching public_domain exactly (e.g. different protocol)
            if key.startswith('http'):
                # Try to split by the last occurrence of the bucket path structure if possible, 
                # but for now let's assume the key is what's after the domain.
                # A safer bet if we saved the key directly would be better, but we saved the full URL.
                # Let's try to parse it.
                from urllib.parse import urlparse
                parsed = urlparse(key)
                # The path usually starts with / so strip it
                key = parsed.path.lstrip('/')

            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=key
            )
            return True
        except ClientError as e:
            print(f"Error deleting file from R2: {e}")
            return False

    def get_presigned_url(self, key, expiration=3600):
        """Generate a presigned URL to share an S3 object"""
        if not self.s3_client:
            return None
        try:
            # If the key is actually a full URL, try to extract the key
            if key.startswith('http'):
                from urllib.parse import urlparse
                parsed = urlparse(key)
                key = parsed.path.lstrip('/')

            response = self.s3_client.generate_presigned_url('get_object',
                                                            Params={'Bucket': self.bucket_name,
                                                                    'Key': key},
                                                            ExpiresIn=expiration)
            return response
        except ClientError as e:
            print(f"Error generating presigned URL: {e}")
            return None

storage_service = StorageService()
