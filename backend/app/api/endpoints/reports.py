from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
import os
from typing import Dict, Any, List
import json
from weasyprint import HTML, CSS
from jinja2 import Environment, FileSystemLoader
import matplotlib.pyplot as plt
import io
import base64
import numpy as np

router = APIRouter()

@router.post("/generate-pdf", response_class=FileResponse)
async def generate_pdf_report(report_data: Dict[str, Any]):
    """Generate a PDF report from the plagiarism data"""
    try:
        # Create report directory if it doesn't exist
        os.makedirs("reports", exist_ok=True)
        
        # Generate charts
        pie_chart = generate_pie_chart(report_data["plagiarismPercentage"])
        sources_chart = generate_sources_chart(report_data["matches"])
        
        # Load HTML template
        env = Environment(loader=FileSystemLoader("app/templates"))
        template = env.get_template("report_template.html")
        
        # Render HTML with data
        html_content = template.render(
            plagiarism_percentage=report_data["plagiarismPercentage"],
            matches=report_data["matches"],
            full_text=report_data["fullTextWithHighlights"],
            pie_chart=pie_chart,
            sources_chart=sources_chart,
            date=report_data.get("date", "")
        )
        
        # Generate PDF from HTML
        report_path = "reports/plagiarism_report.pdf"
        HTML(string=html_content).write_pdf(
            report_path,
            stylesheets=[CSS("app/templates/report_style.css")]
        )
        
        return FileResponse(
            path=report_path, 
            filename="plagiarism_report.pdf",
            media_type="application/pdf"
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {str(e)}")

def generate_pie_chart(plagiarism_percentage: float) -> str:
    """Generate a pie chart as base64 encoded image"""
    plt.figure(figsize=(6, 6))
    labels = ['Plagiarized', 'Original']
    sizes = [plagiarism_percentage, 100 - plagiarism_percentage]
    colors = ['#ff7675' if plagiarism_percentage > 30 else '#fdcb6e', '#74b9ff']
    
    plt.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90)
    plt.axis('equal')
    
    # Save chart to memory
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png')
    buffer.seek(0)
    
    # Convert to base64
    image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
    plt.close()
    
    return f"data:image/png;base64,{image_base64}"

def generate_sources_chart(matches: List[Dict[str, Any]]) -> str:
    """Generate a chart of source distribution"""
    # Extract domains from matches
    domains = {}
    for match in matches:
        try:
            from urllib.parse import urlparse
            domain = urlparse(match["sourceUrl"]).netloc
            domains[domain] = domains.get(domain, 0) + 1
        except:
            pass
    
    # Sort and take top 5
    top_domains = dict(sorted(domains.items(), key=lambda x: x[1], reverse=True)[:5])
    
    # Create bar chart
    plt.figure(figsize=(8, 5))
    plt.bar(top_domains.keys(), top_domains.values(), color='#74b9ff')
    plt.title('Top Sources')
    plt.ylabel('Number of Matches')
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    
    # Save chart to memory
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png')
    buffer.seek(0)
    
    # Convert to base64
    image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
    plt.close()
    
    return f"data:image/png;base64,{image_base64}"