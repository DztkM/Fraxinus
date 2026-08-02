const API_BASE = 'http://localhost:8000';

export class B2BApiClient {
  private token: string | null = null;
  private userId: string | null = null;

  async authenticate(apiKey: string, userId: string) {
    const response = await fetch(`${API_BASE}/v1/api/b2b/auth/token`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ api_key: apiKey })
    });

    if (!response.ok) {
      throw new Error('Authentication failed. Check your API Key.');
    }

    const data = await response.json();
    this.token = data.access_token;
    this.userId = userId;
  }

  getHeaders() {
    if (!this.token || !this.userId) {
      throw new Error('Not authenticated');
    }
    return {
      'Authorization': `Bearer ${this.token}`,
      'X-User-Id': this.userId
    };
  }

  async listFiles() {
    const response = await fetch(`${API_BASE}/api/files/`, {
      headers: this.getHeaders()
    });
    if (!response.ok) throw new Error('Failed to list files');
    return response.json();
  }

  async initUpload(file: File, partsCount: number) {
    const response = await fetch(`${API_BASE}/api/files/upload/init`, {
      method: 'POST',
      headers: {
        ...this.getHeaders(),
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        size: file.size,
        mime_type: file.type || 'application/octet-stream',
        original_name: file.name,
        parts_count: partsCount,
        folder_id: null
      })
    });
    if (!response.ok) throw new Error('Failed to init upload');
    return response.json();
  }

  async uploadPart(url: string, data: Blob) {
    const response = await fetch(url, {
      method: 'PUT',
      body: data
    });
    if (!response.ok) throw new Error('Failed to upload part');
    return response.headers.get('ETag') || '';
  }

  async completeUpload(fileId: string, uploadId: string, parts: { PartNumber: number; ETag: string }[]) {
    const response = await fetch(`${API_BASE}/api/files/${fileId}/upload/complete`, {
      method: 'POST',
      headers: {
        ...this.getHeaders(),
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        upload_id: uploadId,
        parts
      })
    });
    if (!response.ok) throw new Error('Failed to complete upload');
    return response.json();
  }

  async getDownloadUrl(fileId: string) {
    const response = await fetch(`${API_BASE}/api/files/${fileId}/download`, {
      headers: this.getHeaders()
    });
    if (!response.ok) throw new Error('Failed to get download URL');
    return response.json();
  }

  async deleteFile(fileId: string) {
    const response = await fetch(`${API_BASE}/api/files/${fileId}`, {
      method: 'DELETE',
      headers: this.getHeaders()
    });
    if (!response.ok) throw new Error('Failed to delete file');
  }

  // Helper for multipart upload
  async uploadFile(file: File, onProgress: (percent: number) => void) {
    const PART_SIZE = 5 * 1024 * 1024; // 5MB MinIO part size minimum usually
    const partsCount = Math.ceil(file.size / PART_SIZE) || 1;
    
    // 1. Init
    const { file_id, upload_id, presigned_urls } = await this.initUpload(file, partsCount);
    
    // 2. Upload parts
    const completedParts = [];
    let uploadedBytes = 0;

    for (let i = 1; i <= partsCount; i++) {
      const start = (i - 1) * PART_SIZE;
      const end = Math.min(start + PART_SIZE, file.size);
      const chunk = file.slice(start, end);
      
      const etag = await this.uploadPart(presigned_urls[i], chunk);
      
      // Clean up ETag quotes (MinIO sometimes returns them with quotes)
      const cleanEtag = etag.replace(/"/g, ''); 
      
      completedParts.push({ PartNumber: i, ETag: cleanEtag });
      
      uploadedBytes += chunk.size;
      onProgress(Math.round((uploadedBytes / file.size) * 100));
    }

    // 3. Complete
    await this.completeUpload(file_id, upload_id, completedParts);
  }
}

export const api = new B2BApiClient();
