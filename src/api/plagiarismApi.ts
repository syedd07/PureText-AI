import { PlagiarismResponse, StatusResponse, ResultResponse } from '../types/api';

const API_BASE_URL = 'https://puretext-api.azurewebsites.net';

export const checkPlagiarism = async (content: string | File): Promise<PlagiarismResponse> => {
  if (typeof content === 'string') {
    // For text input, use FormData since that's what your backend expects
    let formData = new FormData();
    formData.append('text_input', content);
    
    const response = await fetch(`${API_BASE_URL}/analyze`, {
      method: 'POST',
      body: formData,
    });
    
    if (!response.ok) {
      const errorText = await response.text();
      console.error('API Error:', errorText);
      throw new Error('Failed to initiate plagiarism check');
    }
    
    return await response.json();
  } else {
    // For files, continue using FormData
    let formData = new FormData();
    formData.append('file', content);
    
    const response = await fetch(`${API_BASE_URL}/analyze`, {
      method: 'POST',
      body: formData,
    });
    
    if (!response.ok) {
      const errorText = await response.text();
      console.error('API Error:', errorText);
      throw new Error('Failed to initiate plagiarism check');
    }
    
    return await response.json();
  }
};

export const checkStatus = async (jobId: string): Promise<StatusResponse> => {
  const response = await fetch(`${API_BASE_URL}/status/${jobId}`);
  
  if (!response.ok) {
    throw new Error('Failed to check job status');
  }
  
  return await response.json();
};

export const startPlagiarismCheck = async (jobId: string): Promise<StatusResponse> => {
  const response = await fetch(`${API_BASE_URL}/plagiarism-check/${jobId}`, {
    method: 'POST'
  });
  
  if (!response.ok) {
    throw new Error('Failed to start plagiarism check');
  }
  
  return await response.json();
};

export const getResults = async (jobId: string): Promise<ResultResponse> => {
  const response = await fetch(`${API_BASE_URL}/results/${jobId}`);
  
  if (!response.ok) {
    throw new Error('Failed to get results');
  }
  
  return await response.json();
};


// USE THE MOCK IMPLEMENTATION INSTEAD
/*
export const checkPlagiarism = async (content: string | File): Promise<PlagiarismResponse> => {
  // Simulate API call delay
  await new Promise(resolve => setTimeout(resolve, 1000));
  return { success: true, jobId: "abc123def" };
};

export const checkStatus = async (jobId: string): Promise<StatusResponse> => {
  // Simulate API call delay
  await new Promise(resolve => setTimeout(resolve, 1000));
  return { status: "completed" };
};

export const getResults = async (jobId: string): Promise<ResultResponse> => {
  // Simulate API call delay
  await new Promise(resolve => setTimeout(resolve, 1000));
  return {
    success: true,
    plagiarismPercentage: 45,
    matches: [
      {
        textSnippet: "This is an example copied sentence.",
        sourceUrl: "https://example.com/source1"
      },
      {
        textSnippet: "Another matching phrase from another source.",
        sourceUrl: "https://example.com/source2"
      }
    ],
    fullTextWithHighlights: "<p>This is <mark>an example copied</mark> sentence but other parts are original.</p>"
  };
};

*/