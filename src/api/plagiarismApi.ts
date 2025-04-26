
interface PlagiarismResponse {
  success: boolean;
  jobId: string;
}

interface StatusResponse {
  status: "processing" | "completed" | "failed";
}

interface Match {
  textSnippet: string;
  sourceUrl: string;
}

interface ResultResponse {
  success: boolean;
  plagiarismPercentage: number;
  matches: Match[];
  fullTextWithHighlights: string;
}

// Simulated API calls with dummy responses
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
