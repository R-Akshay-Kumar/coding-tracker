import { useState } from 'react'
import axios from 'axios'
import './App.css'

function App() {
  const [file, setFile] = useState(null)
  
  // LOGIC: We use arrays now (['']) instead of strings ('')
  const [cfProblems, setCfProblems] = useState([''])
  const [lcProblems, setLcProblems] = useState([''])
  const [ccProblems, setCcProblems] = useState([''])
  
  const [loading, setLoading] = useState(false)
  const [downloadUrl, setDownloadUrl] = useState(null)

  const updateProblem = (setFunc, list, index, value) => {
    const updated = [...list]
    updated[index] = value
    setFunc(updated)
  }
  
  const addInput = (setFunc, list) => setFunc([...list, ''])
  
  const removeInput = (setFunc, list, index) => {
    const updated = list.filter((_, i) => i !== index)
    setFunc(updated)
  }

  const handleFileChange = (e) => setFile(e.target.files[0])

  const handleSubmit = async () => {
    if (!file) {
      alert("Please upload a student file first!")
      return
    }
    setLoading(true)
    setDownloadUrl(null)

    const formData = new FormData()
    formData.append("file", file)
    
    // Append all non-empty inputs
    cfProblems.forEach(p => { if(p) formData.append("cf_problems", p) })
    lcProblems.forEach(p => { if(p) formData.append("lc_problems", p) })
    ccProblems.forEach(p => { if(p) formData.append("cc_problems", p) })

    try {
      const response = await axios.post("http://127.0.0.1:8000/check-status", formData, {
        responseType: 'blob',
      })
      const url = window.URL.createObjectURL(new Blob([response.data]))
      setDownloadUrl(url)
    } catch (error) {
      console.error("Error:", error)
      alert("Something went wrong! Check the console.")
    } finally {
      setLoading(false)
    }
  }

  const renderSection = (title, list, setFunc, placeholder) => (
    <div className="input-group">
      <label>{title}</label>
      {list.map((prob, index) => (
        <div key={index} className="dynamic-row">
          <input 
            type="text" 
            placeholder={placeholder}
            value={prob}
            onChange={(e) => updateProblem(setFunc, list, index, e.target.value)}
          />
          {/* Subtle Remove Button */}
          {list.length > 1 && (
            <button className="icon-btn remove" onClick={() => removeInput(setFunc, list, index)}>✕</button>
          )}
        </div>
      ))}
      <button className="text-btn add" onClick={() => addInput(setFunc, list)}>+ Add Another</button>
    </div>
  )

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
        {renderSection("Codeforces IDs", cfProblems, setCfProblems, "e.g. 231A")}
        {renderSection("LeetCode Slugs", lcProblems, setLcProblems, "e.g. two-sum")}
        {renderSection("CodeChef Codes", ccProblems, setCcProblems, "e.g. SANDWSHOP")}
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