
import { useState } from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useToast } from "@/components/ui/use-toast";
import FileUploader from '@/components/FileUploader';
import TextInput from '@/components/TextInput';
import Results from '@/components/Results';
import { checkPlagiarism, checkStatus, getResults } from '@/api/plagiarismApi';

const Index = () => {
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<any>(null);
  const { toast } = useToast();

  const handleSubmission = async (content: string | File) => {
    setLoading(true);
    try {
      const { jobId } = await checkPlagiarism(content);
      
      // Poll for status
      const intervalId = setInterval(async () => {
        const { status } = await checkStatus(jobId);
        if (status === "completed") {
          clearInterval(intervalId);
          const results = await getResults(jobId);
          setResults(results);
          setLoading(false);
        } else if (status === "failed") {
          clearInterval(intervalId);
          setLoading(false);
          toast({
            title: "Error",
            description: "Failed to process your request. Please try again.",
            variant: "destructive",
          });
        }
      }, 2000);
    } catch (error) {
      setLoading(false);
      toast({
        title: "Error",
        description: "An error occurred. Please try again.",
        variant: "destructive",
      });
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-4xl mx-auto px-4 py-8">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            Plagiarism Checker
          </h1>
          <p className="text-gray-600">
            Check your text for plagiarism using our advanced detection tool
          </p>
        </div>

        {!loading && !results && (
          <div className="bg-white p-6 rounded-lg shadow-sm border">
            <Tabs defaultValue="text" className="w-full">
              <TabsList className="grid w-full grid-cols-2">
                <TabsTrigger value="text">Check Text</TabsTrigger>
                <TabsTrigger value="file">Upload File</TabsTrigger>
              </TabsList>
              <TabsContent value="text" className="mt-6">
                <TextInput onSubmit={handleSubmission} />
              </TabsContent>
              <TabsContent value="file" className="mt-6">
                <FileUploader onFileSelect={handleSubmission} />
              </TabsContent>
            </Tabs>
          </div>
        )}

        {loading && (
          <div className="text-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4" />
            <p className="text-gray-600">Analyzing your content for plagiarism...</p>
          </div>
        )}

        {results && (
          <Results
            plagiarismPercentage={results.plagiarismPercentage}
            matches={results.matches}
            fullTextWithHighlights={results.fullTextWithHighlights}
          />
        )}
      </div>
    </div>
  );
};

export default Index;
