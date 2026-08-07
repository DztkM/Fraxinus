const API_BASE_URL = 'http://localhost:8000';

export interface FileItem {
  id: string;
  original_name: string;
  status: string;
  set_access_level: number;
  actual_access_level: number;
  author_id: string;
  created_at: string;
}

export interface FolderItem {
  id: string;
  name: string;
  parent_id: string | null;
  path: string | null;
  set_access_level: number;
  actual_access_level: number;
  author_id: string;
  created_at: string;
}

export interface FolderContents {
  folders: FolderItem[];
  files: FileItem[];
}

export interface SharedItem {
  id: string;
  name: string;
  author_id: string;
  status: string | null;
  created_at: string;
  type: 'file' | 'folder';
}

async function extractErrorMessage(res: Response): Promise<string> {
  try {
    const data = await res.json();
    return data.detail || JSON.stringify(data);
  } catch {
    return `${res.status} ${res.statusText}`;
  }
}

const CHUNK_SIZE = 5 * 1024 * 1024; // 5MB

export async function fetchFiles(token: string): Promise<FileItem[]> {
  console.log("Fetching files with token:", token ? `${token.substring(0, 10)}...` : "NO_TOKEN");
  const res = await fetch(`${API_BASE_URL}/v1/api/files/?limit=100`, {
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

export async function fetchFolderContents(token: string, folderId: string | 'root'): Promise<FolderContents> {
  const url = folderId === 'root' 
    ? `${API_BASE_URL}/v1/api/folders/root/contents`
    : `${API_BASE_URL}/v1/api/folders/${folderId}/contents`;
    
  const res = await fetch(url, {
    headers: {
      Authorization: `Bearer ${token}`
    }
  });
  if (!res.ok) {
    const errText = await res.text();
    throw new Error(`Failed to fetch folder contents: ${res.status} ${res.statusText} - ${errText}`);
  }
  return res.json();
}

export async function createFolder(token: string, name: string, parentId?: string | null): Promise<FolderItem> {
  const body: any = { name };
  if (parentId && parentId !== 'root') {
    body.parent_id = parentId;
  }
  
  const res = await fetch(`${API_BASE_URL}/v1/api/folders/`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(body)
  });
  
  if (!res.ok) {
    const errText = await res.text();
    throw new Error(`Failed to create folder: ${res.status} ${res.statusText} - ${errText}`);
  }
  return res.json();
}

export async function downloadFile(token: string, fileId: string): Promise<string> {
  const res = await fetch(`${API_BASE_URL}/v1/api/files/${fileId}/download`, {
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
  
  return url;
}

export async function uploadFile(
  token: string, 
  file: File, 
  onProgress?: (progress: number) => void,
  folderId?: string | null
): Promise<void> {
  const partsCount = Math.ceil(file.size / CHUNK_SIZE) || 1;

  const initPayload: any = {
    original_name: file.name,
    size: file.size,
    mime_type: file.type || 'application/octet-stream',
    parts_count: partsCount
  };
  
  if (folderId && folderId !== 'root') {
    initPayload.folder_id = folderId;
  }

  // 1. Init upload
  const initRes = await fetch(`${API_BASE_URL}/v1/api/files/upload/init`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(initPayload)
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
  const completeRes = await fetch(`${API_BASE_URL}/v1/api/files/${fileId}/upload/complete`, {
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

export async function renameFolder(token: string, folderId: string, name: string): Promise<FolderItem> {
  const res = await fetch(`${API_BASE_URL}/v1/api/folders/${folderId}`, {
    method: 'PATCH',
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ name })
  });
  if (!res.ok) {
    const detail = await extractErrorMessage(res);
    throw new Error(detail);
  }
  return res.json();
}

export async function deleteFolder(token: string, folderId: string): Promise<void> {
  const res = await fetch(`${API_BASE_URL}/v1/api/folders/${folderId}`, {
    method: 'DELETE',
    headers: {
      Authorization: `Bearer ${token}`
    }
  });
  if (!res.ok) {
    const detail = await extractErrorMessage(res);
    throw new Error(detail);
  }
}

export async function renameFile(token: string, fileId: string, originalName: string): Promise<FileItem> {
  const res = await fetch(`${API_BASE_URL}/v1/api/files/${fileId}`, {
    method: 'PATCH',
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ original_name: originalName })
  });
  if (!res.ok) {
    const detail = await extractErrorMessage(res);
    throw new Error(detail);
  }
  return res.json();
}

export async function deleteFile(token: string, fileId: string): Promise<void> {
  const res = await fetch(`${API_BASE_URL}/v1/api/files/${fileId}`, {
    method: 'DELETE',
    headers: {
      Authorization: `Bearer ${token}`
    }
  });
  if (!res.ok) {
    const detail = await extractErrorMessage(res);
    throw new Error(detail);
  }
}

export async function updateFolderAccess(
  token: string, 
  folderId: string, 
  level: number, 
  allowedUsers?: string[]
): Promise<FolderItem> {
  const body: any = { set_access_level: level };
  if (level === 2 && allowedUsers) {
    body.allowed_users = allowedUsers;
  }
  
  const res = await fetch(`${API_BASE_URL}/v1/api/folders/${folderId}/access`, {
    method: 'PATCH',
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(body)
  });
  if (!res.ok) {
    const detail = await extractErrorMessage(res);
    throw new Error(detail);
  }
  return res.json();
}

export async function updateFileAccess(
  token: string, 
  fileId: string, 
  level: number, 
  allowedUsers?: string[]
): Promise<FileItem> {
  const body: any = { set_access_level: level };
  if (level === 2 && allowedUsers) {
    body.allowed_users = allowedUsers;
  }

  const res = await fetch(`${API_BASE_URL}/v1/api/files/${fileId}/access`, {
    method: 'PATCH',
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(body)
  });
  if (!res.ok) {
    const detail = await extractErrorMessage(res);
    throw new Error(detail);
  }
  return res.json();
}

export async function fetchSharedItems(token: string): Promise<SharedItem[]> {
  const res = await fetch(`${API_BASE_URL}/v1/api/shared/`, {
    headers: {
      Authorization: `Bearer ${token}`
    }
  });
  
  if (!res.ok) {
    const errText = await extractErrorMessage(res);
    throw new Error(`Failed to fetch shared items: ${errText}`);
  }
  const data = await res.json();
  return data.items;
}
