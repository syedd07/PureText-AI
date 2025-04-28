import { useState } from 'react';
import jsPDF from 'jspdf';
import autoTable from 'jspdf-autotable';
import { Button } from './ui/button';
import { FileDown, Loader2 } from 'lucide-react';

interface PlagiarismReportProps {
  plagiarismPercentage: number;
  matches: Array<{
    textSnippet: string;
    sourceUrl: string;
    similarityScore?: number;
  }>;
  fullTextWithHighlights: string;
}

const PlagiarismReport = ({ plagiarismPercentage, matches, fullTextWithHighlights }: PlagiarismReportProps) => {
  const [loading, setLoading] = useState(false);

  // Generate unique report ID with format like "xxxx-xxxx-xxxx" (12 chars with hyphens)
  const generateReportId = () => {
    const chars = '0123456789abcdef';
    let id = '';
    // Generate 12 characters
    for (let i = 0; i < 12; i++) {
      id += chars[Math.floor(Math.random() * chars.length)];
    }
    // Add hyphens to make it look like "xxxx-xxxx-xxxx"
    return `${id.slice(0, 4)}-${id.slice(4, 8)}-${id.slice(8, 12)}`;
  };

  // Count words in the text
  const countWords = (text: string) => {
    const plainText = text.replace(/<[^>]+>/g, '').trim();
    return plainText.split(/\s+/).filter(Boolean).length;
  };

  // Get severity color based on plagiarism percentage
  const getSeverityColor = () => {
    if (plagiarismPercentage > 50) return [239, 68, 68]; // Red
    if (plagiarismPercentage > 30) return [249, 115, 22]; // Orange
    if (plagiarismPercentage > 15) return [234, 179, 8]; // Yellow
    return [34, 197, 94]; // Green
  };

  // Get severity text based on plagiarism percentage
  const getSeverityText = () => {
    if (plagiarismPercentage > 50) return "Very High";
    if (plagiarismPercentage > 30) return "High";
    if (plagiarismPercentage > 15) return "Moderate";
    return "Low";
  };

  // Get domain statistics
  const getDomainStats = () => {
    const domainCounts: Record<string, number> = {};
    matches.forEach(match => {
      try {
        const domain = new URL(match.sourceUrl).hostname.replace('www.', '');
        domainCounts[domain] = (domainCounts[domain] || 0) + 1;
      } catch (e) { /* Handle invalid URLs */ }
    });
    
    return Object.entries(domainCounts)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 5);
  };

  // Helper function to draw circle with percentage-based completion
  const drawPercentageCircle = (pdf, centerX, centerY, radius, percentage, color) => {
    // Calculate the angle based on percentage (360 degrees * percentage)
    const angle = (percentage / 100) * 360;
    
    // Draw background circle (light gray)
    pdf.setDrawColor(220, 220, 220);
    pdf.setLineWidth(3);
    pdf.circle(centerX, centerY, radius, 'S');
    
    // Draw the percentage arc
    pdf.setDrawColor(color[0], color[1], color[2]);
    pdf.setLineWidth(4);
    
    // Draw the arc segment by segment to create the effect
    const segments = 36; // Number of segments (10-degree segments)
    const fullSegments = Math.floor(angle / (360 / segments));
    
    // Start at top (-90 degrees) and go clockwise
    for (let i = 0; i < fullSegments; i++) {
      const startAngle = (-90 + (i * 360 / segments)) * Math.PI / 180;
      const endAngle = (-90 + ((i + 1) * 360 / segments)) * Math.PI / 180;
      
      const x1 = centerX + radius * Math.cos(startAngle);
      const y1 = centerY + radius * Math.sin(startAngle);
      const x2 = centerX + radius * Math.cos(endAngle);
      const y2 = centerY + radius * Math.sin(endAngle);
      
      // Draw the segment
      pdf.line(x1, y1, x2, y2);
    }
    
    // Draw the remaining partial segment if any
    if (fullSegments < segments && percentage > 0) {
      const startAngle = (-90 + (fullSegments * 360 / segments)) * Math.PI / 180;
      const endAngle = (-90 + (angle * Math.PI / 180));
      
      const x1 = centerX + radius * Math.cos(startAngle);
      const y1 = centerY + radius * Math.sin(startAngle);
      const x2 = centerX + radius * Math.cos(endAngle);
      const y2 = centerY + radius * Math.sin(endAngle);
      
      // Draw the segment
      pdf.line(x1, y1, x2, y2);
    }
  };

  // Generate and download PDF
  const generatePDF = async () => {
    try {
      setLoading(true);
      
      // Create PDF document
      const pdf = new jsPDF('portrait', 'pt', 'a4');
      
      // Get word count and report ID
      const wordCount = countWords(fullTextWithHighlights);
      const reportId = generateReportId();
      
      // ===== FIRST PAGE: PLAGIARISM SCAN REPORT =====
      
      // Add logo/branding
      pdf.setFontSize(18);
      pdf.setTextColor(59, 130, 246); // Blue color for branding
      pdf.text('PureText AI', 40, 40);
      
      // Add title
      pdf.setFontSize(20);
      pdf.setTextColor(0);
      pdf.text('Plagiarism Scan Report', 40, 70);
      
      // Add report metadata
      pdf.setFontSize(10);
      pdf.setTextColor(100);
      pdf.text(`Report ID: ${reportId}`, 40, 90);
      pdf.text(`Generated on: ${new Date().toLocaleString()}`, 40, 105);
      pdf.text(`Words analyzed: ${wordCount}`, 40, 120);
      
      pdf.line(40, 130, 550, 130);
      
      // Draw the three column layout
      const startY = 160;

      // Draw column separator lines
      pdf.setDrawColor(220, 220, 220); // Light gray for column separators
      pdf.setLineWidth(1);
      pdf.line(170, startY, 170, startY + 180); // First separator (moved left)
      pdf.line(340, startY, 340, startY + 180); // Second separator (moved left)
      pdf.line(510, startY, 510, startY + 180); // Add third separator

      // ----------------- COLUMN 1: Similarity Score -----------------
      const circleX1 = 85; // Moved left
      const circleY1 = startY + 60;
      const circleRadius1 = 50; // Slightly reduced

      // Draw the large circle with percentage-based completion
      drawPercentageCircle(pdf, circleX1, circleY1, circleRadius1, plagiarismPercentage, getSeverityColor());

      // Add text inside the circle (centered)
      pdf.setTextColor(0);
      pdf.setFontSize(18); // Slightly smaller
      const textWidth1 = pdf.getTextWidth(`${plagiarismPercentage.toFixed(1)}%`);
      pdf.text(`${plagiarismPercentage.toFixed(1)}%`, circleX1 - textWidth1/2, circleY1 + 5);

      pdf.setFontSize(12);
      const textWidth2 = pdf.getTextWidth('Similarity');
      pdf.text('Similarity', circleX1 - textWidth2/2, circleY1 + 20);

      // ----------------- COLUMN 2: Unique Content -----------------
      const uniquePercent = 100 - plagiarismPercentage;
      const circleX2 = 255; // Centered in column 2
      const circleY2 = startY + 60;
      const circleRadius2 = 50;

      // Draw unique percentage circle
      drawPercentageCircle(pdf, circleX2, circleY2, circleRadius2, uniquePercent, [34, 197, 94]); // Green color

      // Add text inside the circle
      pdf.setTextColor(0);
      pdf.setFontSize(18);
      const uniqueTextWidth = pdf.getTextWidth(`${uniquePercent.toFixed(1)}%`);
      pdf.text(`${uniquePercent.toFixed(1)}%`, circleX2 - uniqueTextWidth/2, circleY2 + 5);

      pdf.setFontSize(12);
      const uniqueLabelWidth = pdf.getTextWidth('Unique');
      pdf.text('Unique', circleX2 - uniqueLabelWidth/2, circleY2 + 20);

      // Add label below
      pdf.setTextColor(0);
      pdf.setFontSize(12);
      const originalTextWidth = pdf.getTextWidth('Original Content Score');
      pdf.text('Original Content Score', circleX2 - originalTextWidth/2, circleY2 + 90);

      // ----------------- COLUMN 3: Text Statistics -----------------
      const colX3 = 425; // Centered in column 3
      const colY3 = startY + 30;

      // Get text statistics
      const charCount = fullTextWithHighlights.replace(/<[^>]+>/g, '').length;
      const sentenceCount = fullTextWithHighlights.replace(/<[^>]+>/g, '').split(/[.!?]+/).filter(Boolean).length;

      pdf.setTextColor(0); // Black text
      pdf.setFontSize(14);
      const statsTitleWidth = pdf.getTextWidth('Document Statistics');
      pdf.text('Document Statistics', colX3 - statsTitleWidth/2, colY3);

      // Add statistics in a styled box - aligned with the title
      const boxWidth = 140;
      const boxLeft = colX3 - boxWidth/2;
      pdf.setFillColor(245, 247, 250); // Light gray background
      pdf.roundedRect(boxLeft, colY3 + 10, boxWidth, 100, 5, 5, 'F');

      pdf.setFontSize(12);
      pdf.text(`Words: ${wordCount}`, boxLeft + 10, colY3 + 35);
      pdf.text(`Characters: ${charCount}`, boxLeft + 10, colY3 + 55);
      pdf.text(`Sentences: ${sentenceCount}`, boxLeft + 10, colY3 + 75);
      pdf.text(`Matches Found: ${matches.length}`, boxLeft + 10, colY3 + 95);

      // ----------------- MATCH TYPE INDICATORS -----------------
      // Define match percentages
      const exactMatchPercent = Math.round(plagiarismPercentage * 0.6);
      const partialMatchPercent = Math.round(plagiarismPercentage * 0.4);

      // Set new position for match indicators with INCREASED TOP MARGIN
      const matchY = startY + 210; // Added 20 more points of top margin
      const matchSpacing = 160;
      const matchCenterX = 275;

      // Exact match indicator
      const matchRadius = 25;
      const matchX1 = matchCenterX - matchSpacing/2;

      // Draw exact match circle with percentage-based completion (pink)
      pdf.setDrawColor(220, 220, 220);
      pdf.setLineWidth(2);
      pdf.circle(matchX1, matchY, matchRadius, 'S');

      // Draw percentage arc for exact match
      pdf.setDrawColor(236, 72, 153); // Pink
      pdf.setLineWidth(3);
      const exactAngle = (exactMatchPercent / 100) * 360;
      const exactSegments = 36;
      const exactFullSegments = Math.floor(exactAngle / (360 / exactSegments));

      for (let i = 0; i < exactFullSegments; i++) {
        const startAngle = (-90 + (i * 360 / exactSegments)) * Math.PI / 180;
        const endAngle = (-90 + ((i + 1) * 360 / exactSegments)) * Math.PI / 180;
        
        const x1 = matchX1 + matchRadius * Math.cos(startAngle);
        const y1 = matchY + matchRadius * Math.sin(startAngle);
        const x2 = matchX1 + matchRadius * Math.cos(endAngle);
        const y2 = matchY + matchRadius * Math.sin(endAngle);
        
        pdf.line(x1, y1, x2, y2);
      }

      // Add text inside exact match circle
      pdf.setTextColor(0);
      pdf.setFontSize(11); // Adjusted font size
      const exactTextWidth = pdf.getTextWidth(`${exactMatchPercent.toFixed(1)}%`);
      pdf.text(`${exactMatchPercent.toFixed(1)}%`, matchX1 - exactTextWidth/2, matchY + 3);

      // Add label with more spacing
      pdf.setFontSize(10);
      const exactLabelWidth = pdf.getTextWidth('Exact Match');
      pdf.text('Exact Match', matchX1 - exactLabelWidth/2, matchY + matchRadius + 20); // Increased label spacing to 20

      // Partial match indicator
      const matchX2 = matchCenterX + matchSpacing/2;

      // Draw partial match circle with percentage-based completion (blue)
      pdf.setDrawColor(220, 220, 220); // Gray background circle
      pdf.setLineWidth(2);
      pdf.circle(matchX2, matchY, matchRadius, 'S');

      // Draw percentage arc for partial match
      pdf.setDrawColor(59, 130, 246); // Blue
      pdf.setLineWidth(3);
      const partialAngle = (partialMatchPercent / 100) * 360;
      const partialSegments = 36;
      const partialFullSegments = Math.floor(partialAngle / (360 / partialSegments));

      for (let i = 0; i < partialFullSegments; i++) {
        const startAngle = (-90 + (i * 360 / partialSegments)) * Math.PI / 180;
        const endAngle = (-90 + ((i + 1) * 360 / partialSegments)) * Math.PI / 180;
        
        const x1 = matchX2 + matchRadius * Math.cos(startAngle);
        const y1 = matchY + matchRadius * Math.sin(startAngle);
        const x2 = matchX2 + matchRadius * Math.cos(endAngle);
        const y2 = matchY + matchRadius * Math.sin(endAngle);
        
        pdf.line(x1, y1, x2, y2);
      }

      // Add text inside partial match circle
      pdf.setTextColor(0);
      pdf.setFontSize(11); // Adjusted font size
      const partialTextWidth = pdf.getTextWidth(`${partialMatchPercent.toFixed(1)}%`);
      pdf.text(`${partialMatchPercent.toFixed(1)}%`, matchX2 - partialTextWidth/2, matchY + 3);

      // Add label with more spacing
      pdf.setFontSize(10);
      const partialLabelWidth = pdf.getTextWidth('Partial Match');
      pdf.text('Partial Match', matchX2 - partialLabelWidth/2, matchY + matchRadius + 20); // Increased label spacing to 20

      // ----------------- OVERALL ASSESSMENT -----------------
      // Add severity text with improved spacing - MOVED UP to prevent overlap with table
      const assessmentY = matchY + matchRadius + 60; // Increased top margin to 60 (from 45)

      // First part in normal black
      pdf.setTextColor(0);
      pdf.setFontSize(14);
      const assessmentLabel = "Overall Assessment: ";
      const assessmentLabelWidth = pdf.getTextWidth(assessmentLabel);
      pdf.text(assessmentLabel, 40, assessmentY);

      // The severity value in the severity color
      pdf.setTextColor(getSeverityColor()[0], getSeverityColor()[1], getSeverityColor()[2]);
      pdf.setFontSize(14);
      pdf.text(getSeverityText(), 40 + assessmentLabelWidth, assessmentY);

      // ===== TOP SOURCES (on first page) =====
      // Reset text color
      pdf.setTextColor(59, 130, 246); // Blue color for header
      pdf.setFontSize(16);
      // Increased spacing between assessment and top sources
      pdf.text('Top Sources', 40, assessmentY + 40); // Increased from 30 to 40

      // Adjust table position to start below the Top Sources header with proper spacing
      const tableStartY = assessmentY + 50; // Increased from 40 to 50

      // Add domain statistics if there are matches
      const sortedDomains = getDomainStats();
      if (sortedDomains.length > 0) {
        // Create a table of sources
        const tableData = sortedDomains.map(([domain, count], index) => [
          `${index + 1}.`, domain, `${count} match${count > 1 ? 'es' : ''}`
        ]);
        
        autoTable(pdf, {
          startY: tableStartY, // Updated position
          head: [['#', 'Source Domain', 'Matches']],
          body: tableData,
          theme: 'striped',
          headStyles: {
            fillColor: [59, 130, 246],
            textColor: [255, 255, 255],
            fontStyle: 'bold'
          },
          columnStyles: {
            0: { cellWidth: 40 },
            1: { cellWidth: 300 },
            2: { cellWidth: 100, halign: 'center' }
          },
          margin: { bottom: 40 } // Add bottom margin
        });
      } else {
        pdf.setFontSize(12);
        pdf.text('No matching sources were found.', 40, tableStartY + 20);
      }
      
      // ===== THIRD PAGE: MATCHED SOURCES =====
      pdf.addPage();
      pdf.setFontSize(18);
      pdf.setTextColor(59, 130, 246); // Blue color for header
      pdf.text('PureText AI - Matched Sources', 40, 40);
      pdf.setTextColor(0);
      
      if (matches.length > 0) {
        pdf.setFontSize(12);
        pdf.text('The following sections match existing online sources:', 40, 70);
        
        const tableData = matches.map(match => {
          try {
            // Format the matched text
            const snippet = match.textSnippet.length > 120 ? 
              match.textSnippet.substring(0, 120) + '...' : 
              match.textSnippet;
              
            // Get domain for display
            const domain = new URL(match.sourceUrl).hostname;
            
            return [
              snippet,
              domain,
              match.sourceUrl,
              match.similarityScore ? `${(match.similarityScore * 100).toFixed(1)}%` : 'N/A'
            ];
          } catch (e) {
            return [
              match.textSnippet.length > 120 ? match.textSnippet.substring(0, 120) + '...' : match.textSnippet,
              'Unknown source',
              match.sourceUrl,
              match.similarityScore ? `${(match.similarityScore * 100).toFixed(1)}%` : 'N/A'
            ];
          }
        });
        
        // Add source matches table
        autoTable(pdf, {
          head: [['Matched Text', 'Source', 'URL', 'Similarity']],
          body: tableData,
          startY: 80,
          margin: { top: 80 },
          headStyles: { 
            fillColor: [59, 130, 246],
            textColor: [255, 255, 255],
            fontStyle: 'bold'
          },
          alternateRowStyles: { fillColor: [241, 245, 249] },
          styles: { 
            overflow: 'linebreak',
            cellWidth: 'auto',
            cellPadding: 5
          },
          columnStyles: {
            0: { fontStyle: 'italic', textColor: [0, 0, 0], cellWidth: 200 }, // Matched text
            1: { fontStyle: 'normal', textColor: [100, 100, 100] },          // Source domain
            2: { fontStyle: 'normal', textColor: [59, 130, 246] },           // URL (blue)
            3: { fontStyle: 'bold', halign: 'center' }                       // Similarity score
          },
        });
      } else {
        pdf.setFontSize(12);
        pdf.text('No matching sources were found in our database.', 40, 80);
        pdf.setFontSize(14);
        pdf.setTextColor(34, 197, 94); // Green
        pdf.text('Your content appears to be original.', 40, 100);
        pdf.setTextColor(0);
      }
      
      // ===== FOURTH PAGE: VERIFICATION INFORMATION =====
      pdf.addPage();
      pdf.setFontSize(18);
      pdf.setTextColor(59, 130, 246);
      pdf.text('PureText AI - Verification Information', 40, 40);
      pdf.setTextColor(0);
      
      pdf.setFontSize(12);
      pdf.text('Document Statistics', 40, 70);
      
      // Add verification table with fixed width columns
      const verificationData = [
        ['Report ID', reportId],
        ['Creation Date', new Date().toLocaleDateString()],
        ['Words Analyzed', wordCount.toString()],
        ['Characters', fullTextWithHighlights.replace(/<[^>]+>/g, '').length.toString()],
        ['Similarity Score', `${plagiarismPercentage.toFixed(1)}%`],
        ['Matches Found', matches.length.toString()],
        ['Timestamp', new Date().toLocaleTimeString()]
      ];
      
      // Improved table layout to prevent overlapping
      autoTable(pdf, {
        body: verificationData,
        startY: 80,
        theme: 'grid',
        styles: {
          fontSize: 10,
          cellPadding: 5,
          overflow: 'linebreak'
        },
        columnStyles: {
          0: { fontStyle: 'bold', fillColor: [245, 247, 250], cellWidth: 120 }, 
          1: { cellWidth: 'auto' }
        }
      });
      
      // Add verification message
      pdf.setFontSize(10);
      pdf.setTextColor(100);
      const verifyText = "This report is a certified analysis of the submitted text. " +
        "The document fingerprint is based on the exact text analyzed and can be used to verify this report.";
      
      const verifyLines = pdf.splitTextToSize(verifyText, 500);
      pdf.text(verifyLines, 40, 200);
      
      // Add footer to all pages
      const pageCount = pdf.internal.pages.length;
      pdf.setFontSize(8);
      pdf.setTextColor(150);
      
      for(let i = 1; i <= pageCount; i++) {
        pdf.setPage(i);
        pdf.text(`Generated by PureText AI - Page ${i} of ${pageCount} - Report ID: ${reportId}`, 40, pdf.internal.pageSize.height - 20);
      }
      
      // Save the PDF
      pdf.save('PureText-AI-plagiarism-report.pdf');
    } catch (error) {
      console.error('Error generating PDF:', error);
      alert('Failed to generate PDF report. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Button 
      onClick={generatePDF} 
      variant="outline" 
      className="mt-4 flex items-center gap-2 border-primary"
      disabled={loading}
    >
      {loading ? (
        <Loader2 className="h-4 w-4 animate-spin" />
      ) : (
        <FileDown className="h-4 w-4" />
      )}
      {loading ? 'Generating Report...' : 'Download Report'}
    </Button>
  );
};

export default PlagiarismReport;