const API_BASE = '/api';

export async function uploadFile(file) {
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch(`${API_BASE}/upload`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    throw new Error(`Upload failed: ${response.statusText}`);
  }

  return response.json();
}

export async function getStatus(jobId) {
  const response = await fetch(`${API_BASE}/status/${jobId}`);
  
  if (!response.ok) {
    throw new Error(`Status check failed: ${response.statusText}`);
  }

  return response.json();
}

export async function getTranscript(jobId) {
  const response = await fetch(`${API_BASE}/transcript/${jobId}`);
  
  if (!response.ok) {
    throw new Error(`Transcript fetch failed: ${response.statusText}`);
  }

  return response.json();
}

export async function createSummary(jobId, contextText = '') {
  const response = await fetch(`${API_BASE}/summary/${jobId}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ context_text: contextText }),
  });

  if (!response.ok) {
    throw new Error(`Summary failed: ${response.statusText}`);
  }

  return response.json();
}

export async function downloadSummary(jobId) {
  const response = await fetch(`${API_BASE}/download/${jobId}`);
  
  if (!response.ok) {
    throw new Error(`Download failed: ${response.statusText}`);
  }

  return response.blob();
}

export async function deleteJob(jobId) {
  await fetch(`${API_BASE}/job/${jobId}`, {
    method: 'DELETE',
  });
}

export async function healthCheck() {
  const response = await fetch(`${API_BASE}/health`);
  return response.json();
}
