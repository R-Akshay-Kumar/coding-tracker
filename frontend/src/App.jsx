import { useState } from 'react'
import axios from 'axios'
import './App.css'

function App() {
  const [file, setFile] = useState(null)
  const [cfProblem, setCfProblem] = useState('')
  const [lcProblem, setLcProblem] = useState('')
  const [ccProblem, setCcProblem] = useState('')
  const [loading, setLoading] = useState(false)
  const [downloadUrl, setDownloadUrl] = useState(null)

  const handleFileChange = (e) => {
    setFile(e.target.files[0])
  }

  const handleSubmit = async () => {
    if (!file) {
      alert("Please upload a student file first!")
      return
    }

    setLoading(true)
    setDownloadUrl(null)

    const formData = new FormData()
    formData.append("file", file)
    formData.append("cf_problem", cfProblem)
    formData.append("lc_problem", lcProblem)
    formData.append("cc_problem", ccProblem)

    try {
      // Send data to Python Backend
      const response = await axios.post("http://127.0.0.1:8000/check-status", formData, {
        responseType: 'blob', // Important: We expect a file back, not text
      })

      // Create a download link for the file we just got
      const url = window.URL.createObjectURL(new Blob([response.data]))
      setDownloadUrl(url)
      
    } catch (error) {
      console.error("Error:", error)
      alert("Something went wrong! Check the console.")
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="container">
      <h1>Student Coding Tracker</h1>
      
      <div className="card">
        <h3>1. Upload Student List</h3>
        <input type="file" onChange={handleFileChange} accept=".xlsx, .csv" />
        <p className="hint">Must be .xlsx with headers: Name, CODEFORCES, LEETCODE, CODECHEF</p>
      </div>

      <div className="card">
        <h3>2. Enter Problem IDs</h3>
        
        <div className="input-group">
          <label>Codeforces ID (e.g. 231A)</label>
          <input 
            type="text" 
            placeholder="231A" 
            value={cfProblem}
            onChange={(e) => setCfProblem(e.target.value)}
          />
        </div>

        <div className="input-group">
          <label>LeetCode Slug (e.g. two-sum)</label>
          <input 
            type="text" 
            placeholder="two-sum" 
            value={lcProblem}
            onChange={(e) => setLcProblem(e.target.value)}
          />
        </div>

        <div className="input-group">
          <label>CodeChef Code (e.g. SANDWSHOP)</label>
          <input 
            type="text" 
            placeholder="SANDWSHOP" 
            value={ccProblem}
            onChange={(e) => setCcProblem(e.target.value)}
          />
        </div>
      </div>

      <button 
        className="generate-btn" 
        onClick={handleSubmit} 
        disabled={loading}
      >
        {loading ? "Checking Status (Please Wait)..." : "Generate Report"}
      </button>

      {downloadUrl && (
        <div className="result-area">
          <h3>✅ Report Ready!</h3>
          <a href={downloadUrl} download="Student_Report.xlsx" className="download-btn">
            Download Excel File
          </a>
        </div>
      )}

    </div>
  )
}

export default App