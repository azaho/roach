# Roach: AGI & SCSP Hackathon Project

Roach is a versatile and predictive tool designed to detect, analyze, and filter disinformation narratives across digital platforms. Developed during the AGI & SCSP Hackathon on November 15, 2024, Roach leverages advanced crawling and filtering techniques to identify disinformation patterns and narratives.

[View Project Presentation](https://drive.google.com/file/d/1c_umZbdYyWSTJRDq0mFKB2S7BWIGSKYd/view?usp=sharing)

> **Note**: This project uses an adapted version of the [pyktok](https://github.com/dfreelon/pyktok) library for TikTok data collection.

---

## 🔗 How to run this
1. Clone the repository:
   ```bash
   git clone [repository-url]
   cd roach
   ```

2. Install dependencies:
   ```bash
   pip install openai moviepy python-dotenv pyktok pandas pydantic
   ```

3. Run the main script:
   ```bash
   python outer_loop.py
   ```

   The script starts with a "roach drop" - an initial TikTok video URL that contains potential disinformation. You can modify the `roach_drop` variable in `outer_loop.py` to start from a different video:

   ```python
   roach_drop = 'https://www.tiktok.com/@jeffrey1012/video/7298550647857728786'
   ```

   The script will:
   - Download the initial video
   - Extract comments and transcripts
   - Analyze for disinformation narratives
   - Identify suspicious users from comments
   - Recursively check suspicious users' content
   - Build a network map of disinformation spread


---

## 🚀 How It Works

1. **Sniff**: Collect data from various platforms (e.g., TikTok, Google Docs links, etc.).
2. **Crawl**: Extract relevant metadata, transcripts, and comments for further analysis.
3. **Analyze**:
   - Identify and classify disinformation narratives using a central database of known patterns.
   - Process transcripts and content for mentions of corruption, instability, and similar topics.
4. **Filter**: Highlight and categorize narratives, such as "Corruption allegations in Ukraine."
5. **Predict**: Use patterns to forecast potential spread and impact of disinformation.

---

## 📚 Features

- **Content Scraping**: Gathers data from platforms such as TikTok.
- **Narrative Detection**: Matches extracted data with pre-stored disinformation patterns.
- **Central Database**: Stores narratives and disinformation identifiers for real-time comparison.
- **Versatility**: Works across multiple platforms and formats.
- **Predictive Analysis**: Insights into the evolution and impact of disinformation.

---

## 🔗 Example Workflow

- Crawl TikTok for relevant videos:
  ```json
  {
    "username": "jeffrey1012",
    "timestamp": "2023-11-06T22:04:10",
    "description": "#vladimirzelensky #russia",
    "location": "SG",
    "comments": [
      {
        "username": "nogin.the.nog",
        "text": "There will be no tomorrow for the ukraine, unless they get rid of zelensky.",
        "likes": 1,
        "timestamp": 1700486901
      }
    ],
    "transcript": "A new in-depth profile reveals massive corruption inside Ukraine. That's according to ..."
  }```
- Identify known disinformation narratives:  
  ```json
  {
    "transcript": "A new in-depth profile reveals massive corruption inside Ukraine. That's according to ...",
    "narratives": ["Corruption allegations in Ukraine", "..."]
  }```

  ---

## 🌟 Team Members
- **Dima Yanovsky** ([LinkedIn](https://www.linkedin.com/in/yanovsk/))  
  *MIT Class of 2025*  
- **Laker Newhouse** ([LinkedIn](https://www.linkedin.com/in/lakernewhouse/))  
  *MIT Class of 2025*  
- **Andrii Zahorodnii** ([LinkedIn](https://www.linkedin.com/in/zaho/))  
  *MIT Class of 2024*

---

## 🌐 Resources

- TikTok: [Example Content](https://www.tiktok.com/@jeffrey1012/video/7298550647857728786)
- Google Docs: [Example Dataset](https://docs.google.com/file/d/11-v58gQ8iuUGLnjlXIqfpFKArrZYhlCe/preview)

---

## 📄 License

This project is released under [MIT License](LICENSE).
