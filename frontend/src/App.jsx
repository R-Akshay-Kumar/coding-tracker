import { useState, useEffect } from 'react'
import axios from 'axios'
import './App.css'

function App() {
  const [file, setFile] = useState(null)
  
  // Dynamic Inputs
  const [cfProblems, setCfProblems] = useState([''])
  const [lcProblems, setLcProblems] = useState([''])
  const [ccProblems, setCcProblems] = useState([''])
  
  // Progress State
  const [loading, setLoading] = useState(false)
  const [progress, setProgress] = useState(0)
  const [statusText, setStatusText] = useState("")
  const [downloadUrl, setDownloadUrl] = useState(null)
  const [jobId, setJobId] = useState(null)

  // --- Helpers ---
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


  // --- STEP 1: START JOB ---
  const handleSubmit = async () => {
    if (!file) {
      alert("Please upload a student file first!")
      return
    }
    setLoading(true)
    setDownloadUrl(null)
    setProgress(0)
    setStatusText("Uploading file (this takes few minutes)...")

    const formData = new FormData()
    formData.append("file", file)
    cfProblems.forEach(p => { if(p) formData.append("cf_problems", p) })
    lcProblems.forEach(p => { if(p) formData.append("lc_problems", p) })
    ccProblems.forEach(p => { if(p) formData.append("cc_problems", p) })

    try {
      // START THE JOB ON RENDER
      const response = await axios.post("https://coding-tracker-m505.onrender.com/start-check", formData)
      setJobId(response.data.job_id)
      
    } catch (error) {
      console.error("Error:", error)
      alert("Failed to start job.")
      setLoading(false)
    }
  }

  // --- STEP 2: POLL PROGRESS ---
  useEffect(() => {
    let interval;
    if (jobId && loading) {
      interval = setInterval(async () => {
        try {
          const res = await axios.get(`https://coding-tracker-m505.onrender.com/progress/${jobId}`)
          const data = res.data

          if (data.status === "processing" || data.status === "queued") {
            const current = data.current
            const total = data.total
            
            if (total > 0) {
              const percentage = Math.round((current / total) * 100)
              setProgress(percentage)
              setStatusText(`Checking Student ${current} of ${total}...`)
            } else {
              setStatusText("Preparing list...")
            }

          } else if (data.status === "completed") {
            setProgress(100)
            setStatusText("Finalizing Report...")
            clearInterval(interval)
            fetchDownload(jobId)
          } else if (data.status === "failed") {
            alert("Job failed: " + data.error)
            setLoading(false)
            clearInterval(interval)
          }
        } catch (err) {
          console.error("Polling error", err)
        }
      }, 1000)
    }
    return () => clearInterval(interval)
  }, [jobId, loading])

  // --- STEP 3: DOWNLOAD ---
  const fetchDownload = async (id) => {
    try {
      const response = await axios.get(`https://coding-tracker-m505.onrender.com/download/${id}`, {
        responseType: 'blob',
      })
      const url = window.URL.createObjectURL(new Blob([response.data]))
      setDownloadUrl(url)
      setLoading(false)
      setJobId(null)
    } catch (error) {
      alert("Error downloading file")
    }
  }

  // --- UI RENDER ---
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
      </div>

      <div className="card">
        <h3>2. Enter Problem IDs</h3>
        {renderSection("Codeforces IDs", cfProblems, setCfProblems, "e.g. 231A")}
        {renderSection("LeetCode Slugs", lcProblems, setLcProblems, "e.g. two-sum")}
        {renderSection("CodeChef Codes", ccProblems, setCcProblems, "e.g. SANDWSHOP")}
      </div>

      {!loading ? (
        <button className="generate-btn" onClick={handleSubmit}>
          Generate Report
        </button>
      ) : (
        <div className="progress-container">
          <div className="progress-row">
            <div className="progress-track">
              <div className="progress-fill" style={{ width: `${progress}%` }}></div>
            </div>
            <span className="percentage-text">{progress}%</span>
          </div>
          <p className="status-text">{statusText}</p>
        </div>
      )}

      {downloadUrl && !loading && (
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
