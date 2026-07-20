const API_BASE_URL = 'http://localhost:8000';

export interface FileItem {
  id: string;
  original_name: string;
  status: string;
  set_access_level: number;
  actual_access_level: number;
  created_at: string;
}

const CHUNK_SIZE = 5 * 1024 * 1024; // 5MB

export async function fetchFiles(token: string): Promise<FileItem[]> {
  console.log("Fetching files with token:", token ? `${token.substring(0, 10)}...` : "NO_TOKEN");
  const res = await fetch(`${API_BASE_URL}/api/files/?limit=100`, {
    headers: {
      Authorization: `Bearer ${token}`
    }
  });
  if (!res.ok) {
    const errText = await res.text();
    console.error("Fetch files error:", res.status, errText);
    throw new Error(`Failed to fetch files: ${res.status} ${res.statusText} - ${errText}`);
  }
  return res.json();
}

export async function downloadFile(token: string, fileId: string): Promise<void> {
  const res = await fetch(`${API_BASE_URL}/api/files/${fileId}/download`, {
    headers: {
      Authorization: `Bearer ${token}`
    }
  });
  
  if (!res.ok) {
    throw new Error(`Failed to get download URL: ${res.status} ${res.statusText}`);
  }
  
  const data = await res.json();
  const { url, original_name } = data;
  
  // Create a temporary link element to trigger the download
  const link = document.createElement('a');
  link.href = url;
  link.download = original_name; // Set suggested file name
  // Note: Since we are downloading from S3 pre-signed URL, the Content-Disposition 
  // header should ideally be set in the pre-signed URL to force download.
  // We append it to the body, click it, and remove it.
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}

export async function uploadFile(
  token: string, 
  file: File, 
  onProgress?: (progress: number) => void
): Promise<void> {
  const partsCount = Math.ceil(file.size / CHUNK_SIZE) || 1;

  // 1. Init upload
  const initRes = await fetch(`${API_BASE_URL}/api/files/upload/init`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      original_name: file.name,
      size: file.size,
      mime_type: file.type || 'application/octet-stream',
      parts_count: partsCount
    })
  });

  if (!initRes.ok) {
    throw new Error(`Failed to init upload: ${initRes.status} ${initRes.statusText}`);
  }

  const initData = await initRes.json();
  const fileId = initData.file_id;
  const uploadId = initData.upload_id;
  const urls = initData.presigned_urls;

  const completedParts: { PartNumber: number, ETag: string }[] = [];

  // 2. Upload parts
  for (let partNumber = 1; partNumber <= partsCount; partNumber++) {
    const start = (partNumber - 1) * CHUNK_SIZE;
    const end = Math.min(start + CHUNK_SIZE, file.size);
    const chunk = file.slice(start, end);
    const url = urls[partNumber.toString()];

    const putRes = await fetch(url, {
      method: 'PUT',
      body: chunk
    });

    if (!putRes.ok) {
      throw new Error(`Failed to upload part ${partNumber}: ${putRes.status} ${putRes.statusText}`);
    }

    const etag = putRes.headers.get('ETag');
    if (!etag) {
      // In a real S3 scenario with CORS, ensure ETag is exposed in Access-Control-Expose-Headers.
      // If it's missing, we might still try to pass a dummy or throw.
      // Usually MinIO includes it.
    }
    completedParts.push({
      PartNumber: partNumber,
      ETag: etag || 'MISSING_ETAG' 
    });

    if (onProgress) {
      onProgress(Math.round((partNumber / partsCount) * 100));
    }
  }

  // 3. Complete upload
  const completeRes = await fetch(`${API_BASE_URL}/api/files/${fileId}/upload/complete`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      upload_id: uploadId,
      parts: completedParts
    })
  });

  if (!completeRes.ok) {
    throw new Error(`Failed to complete upload: ${completeRes.status} ${completeRes.statusText}`);
  }
}
