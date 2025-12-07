import os
import boto3
from dotenv import load_dotenv

load_dotenv()

bucket_name = os.environ.get('R2_BUCKET_NAME')
account_id = os.environ.get('R2_ACCOUNT_ID')
access_key = os.environ.get('R2_ACCESS_KEY_ID')
secret_key = os.environ.get('R2_SECRET_ACCESS_KEY')

print(f"Connecting to bucket: {bucket_name}")

try:
    s3 = boto3.client(
        's3',
        endpoint_url=f'https://{account_id}.r2.cloudflarestorage.com',
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name='auto'
    )

    response = s3.list_objects_v2(Bucket=bucket_name)
    
    if 'Contents' in response:
        print("Files found:")
        for obj in response['Contents']:
            print(f"- {obj['Key']} (Size: {obj['Size']})")
            
            # Try to generate a presigned URL for the first file to test
            url = s3.generate_presigned_url(
                'get_object',
                Params={'Bucket': bucket_name, 'Key': obj['Key']},
                ExpiresIn=3600
            )
            print(f"  Presigned URL: {url}")
    else:
        print("No files found in the bucket.")

except Exception as e:
    print(f"Error: {e}")
