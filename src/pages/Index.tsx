import { useState } from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useToast } from "@/components/ui/use-toast";
import FileUploader from '@/components/FileUploader';
import TextInput from '@/components/TextInput';
import Results from '@/components/Results';
import { checkPlagiarism, checkStatus, startPlagiarismCheck, getResults } from '@/api/plagiarismApi';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import { Loader, CheckCircle2, AlertTriangle } from "lucide-react";
import { Button } from "@/components/ui/button";

const Index = () => {
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [currentStep, setCurrentStep] = useState<string>("initializing");
  const [results, setResults] = useState<any>(null);
  const { toast } = useToast();

  const handleSubmission = async (content: string | File) => {
    setLoading(true);
    setProgress(0);
    setCurrentStep("initializing");

    try {
      // Start animation
      setProgress(10);
      setCurrentStep("Initiating plagiarism check...");

      // FIX HERE: Properly extract job_id from response
      const response = await checkPlagiarism(content);
      console.log("API Response:", response); // Debug log

      // Extract job_id correctly
      const jobId = response.job_id; // Use the correct property name

      if (!jobId) {
        throw new Error("No job ID returned from API");
      }

      console.log("Job ID:", jobId); // Confirm job_id was received

      setProgress(30);
      setCurrentStep("Processing content...");

      // Poll for status
      const intervalId = setInterval(async () => {
        setProgress(prev => Math.min(prev + 5, 95)); // Gradually increase progress

        const statusResponse = await checkStatus(jobId);
        const { status } = statusResponse;

        console.log("Current status:", status); // Add debug log
        
        if (status === "analyzed") {
          // Add this block to trigger the plagiarism check when analysis is done
          clearInterval(intervalId);
          setCurrentStep("Starting plagiarism detection...");
          
          try {
            // Call the plagiarism check endpoint to start the source matching
            await startPlagiarismCheck(jobId);
            
            // Start polling again for the final completion
            pollForCompletion(jobId);
          } catch (error) {
            console.error("Error starting plagiarism check:", error);
            setLoading(false);
            toast({
              title: "Error",
              description: "Failed to start plagiarism check. Please try again.",
              variant: "destructive",
            });
          }
        } else if (status === "completed") {
          clearInterval(intervalId);
          setProgress(95);
          setCurrentStep("Finalizing report...");

          setTimeout(async () => {
            const apiResults = await getResults(jobId);
            // console.log("Raw API results:", apiResults);
            
            // Transform snake_case to camelCase
            const transformedResults = {
              plagiarismPercentage: apiResults.plagiarism_percentage,
              matches: apiResults.matches.map(match => ({
                textSnippet: match.text_snippet,
                sourceUrl: match.source_url,
                // Optionally include similarity score if you want to display it
                similarityScore: match.similarity_score
              })),
              fullTextWithHighlights: apiResults.full_text_with_highlights
            };
            
            setResults(transformedResults);
            setLoading(false);
            setProgress(100);
            toast({
              description: "Analysis completed successfully.",
            });
          }, 800);
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

      // Add this helper function to poll for completion
      const pollForCompletion = (jobId: string) => {
        const completionInterval = setInterval(async () => {
          try {
            const statusResponse = await checkStatus(jobId);
            
            if (statusResponse.status === "completed") {
              clearInterval(completionInterval);
              setProgress(95);
              setCurrentStep("Finalizing report...");
              
              setTimeout(async () => {
                const apiResults = await getResults(jobId);
                // console.log("Raw API results:", apiResults);
                
                // Transform snake_case to camelCase
                const transformedResults = {
                  plagiarismPercentage: apiResults.plagiarism_percentage,
                  matches: apiResults.matches.map(match => ({
                    textSnippet: match.text_snippet,
                    sourceUrl: match.source_url,
                    // Optionally include similarity score if you want to display it
                    similarityScore: match.similarity_score
                  })),
                  fullTextWithHighlights: apiResults.full_text_with_highlights
                };
                
                setResults(transformedResults);
                setLoading(false);
                setProgress(100);
                toast({
                  description: "Analysis completed successfully.",
                });
              }, 800);
            } else if (statusResponse.status === "failed") {
              clearInterval(completionInterval);
              setLoading(false);
              toast({
                title: "Error",
                description: "Failed to process your request. Please try again.",
                variant: "destructive",
              });
            }
          } catch (error) {
            console.error("Error checking completion status:", error);
            clearInterval(completionInterval);
            setLoading(false);
            toast({
              title: "Error",
              description: "An error occurred while checking status.",
              variant: "destructive",
            });
          }
        }, 2000);
      };
    } catch (error) {
      setLoading(false);
      toast({
        title: "Error",
        description: "An error occurred. Please try again.",
        variant: "destructive",
      });
    }
  };

  const handleScanAnother = () => {
    setResults(null);
    setLoading(false);
    setProgress(0);
    setCurrentStep("initializing");
  };

  return (
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
        <div className="bg-white rounded-lg shadow-sm border">
          <Tabs defaultValue="text" className="w-full">
            <TabsList className="w-full grid grid-cols-2">
              <TabsTrigger value="text">Check Text</TabsTrigger>
              <TabsTrigger value="file">Upload File</TabsTrigger>
            </TabsList>
            <TabsContent value="text" className="p-6">
              <TextInput onSubmit={handleSubmission} />
            </TabsContent>
            <TabsContent value="file" className="p-6">
              <FileUploader onFileSelect={handleSubmission} />
            </TabsContent>
          </Tabs>
        </div>
      )}

      {loading && (
        <div className="bg-white rounded-lg shadow-sm border p-8 text-center">
          <div className="flex flex-col items-center justify-center min-h-[400px] space-y-8">
            <div className="relative w-48 h-48 flex items-center justify-center">
              {/* Animated Circular Progress */}
              <svg className="absolute w-full h-full -rotate-90" viewBox="0 0 100 100">
                <circle
                  cx="50"
                  cy="50"
                  r="45"
                  fill="transparent"
                  stroke="currentColor"
                  strokeWidth="8"
                  className="text-secondary/30"
                />
                <circle
                  cx="50"
                  cy="50"
                  r="45"
                  fill="transparent"
                  stroke="currentColor"
                  strokeWidth="8"
                  strokeDasharray="283"
                  strokeDashoffset={`${283 * (1 - progress / 100)}`}
                  className="text-primary transition-all duration-500 ease-in-out"
                />
              </svg>

              {/* Animated Loader Icon */}
              <div className="absolute inset-0 flex items-center justify-center animate-pulse">
                <Loader className="w-24 h-24 text-primary/70 animate-spin" />
              </div>
            </div>

            <div className="text-center space-y-4 max-w-md">
              <h3 className="text-2xl font-semibold text-gray-800 animate-fade-in">
                {currentStep}
              </h3>

              <div className="w-full bg-secondary/20 rounded-full h-3 overflow-hidden">
                <div
                  className="bg-primary h-full transition-all duration-300 ease-in-out"
                  style={{ width: `${progress}%` }}
                />
              </div>

              <p className="text-sm text-muted-foreground animate-fade-in">
                {progress}% complete
              </p>

              <Collapsible>
                <CollapsibleTrigger asChild>
                  <Button variant="outline" size="sm" className="mt-4">
                    Show Analysis Details
                  </Button>
                </CollapsibleTrigger>

                <CollapsibleContent>
                  <div className="mt-4 p-4 bg-secondary/10 rounded-lg text-left space-y-3 animate-fade-in">
                    <div className="flex items-center space-x-2">
                      <CheckCircle2 className="w-5 h-5 text-green-500" />
                      <span>Content Analysis</span>
                    </div>
                    <div className="flex items-center space-x-2">
                      <AlertTriangle className="w-5 h-5 text-yellow-500" />
                      <span>Source Matching</span>
                    </div>
                    <p className="text-xs text-muted-foreground">
                      Our advanced AI is meticulously analyzing your content across multiple databases.
                    </p>
                  </div>
                </CollapsibleContent>
              </Collapsible>
            </div>
          </div>
        </div>
      )}

      {results && (
        <Results
          plagiarismPercentage={results.plagiarismPercentage}
          matches={results.matches}
          fullTextWithHighlights={results.fullTextWithHighlights}
          onScanAnother={handleScanAnother}
        />
      )}
    </div>
  );
};

export default Index;
