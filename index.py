import streamlit as st
import obspy
import pandas as pd
import plotly.graph_objects as go
from libraries.omegaArithmetic import intf
import numpy as np
from scipy import signal
from libraries import filter_function
from scipy.signal import find_peaks
from scipy.signal import spectrogram, hanning
from libraries.half_power import dampHalf
from libraries.log_damp import dampLog
import os
from io import BytesIO
import base64


def intro():
    import streamlit as st

    st.write("# Welcome to Acceleration Value Processing Web Page! 👋")
    st.sidebar.success("Select a Page above.")

    st.markdown(
        """

        Web application designed to help you evaluate your acceleration files in an impressive manner. We offer a powerful and user-friendly solution to meet your signal analysis needs. Our goal is to analyze your acceleration data and provide you with valuable insights to enhance your decision-making process.

        Key Features:

        FFT Displacement Calculation: We analyze your acceleration files using Fourier Transform (FFT), allowing you to determine displacement values in the frequency spectrum. This feature is highly beneficial for structural integrity, vibration analysis, and other applications.

        Damping Ratio Calculation: We utilize a specialized algorithm to calculate the damping ratio of vibrations in your acceleration data. This information is crucial for understanding energy loss in vibrations and how the vibration motion slows down within the system.

        Excel Output: We provide output in Excel format, enabling you to easily share your analysis results. You can integrate your data with other tools or share your analysis results with others effortlessly.

        User-Friendly Interface: Our web application offers a user-friendly interface that allows you to easily upload your acceleration files, adjust analysis parameters, and quickly visualize the results. While the analysis process involves complex mathematical calculations, it is handled in the background, and the results are presented in a clear and understandable manner.

        Security and Data Privacy: We prioritize data security and privacy. All your uploaded acceleration files and analysis results are stored on our secure servers, protected by advanced security measures. We have taken necessary precautions to ensure that your data is not shared with third parties or misused.

        Web provides valuable insights in various areas, from structural integrity analysis to vibration issues. It is an ideal solution for industrial sectors, structural engineering firms, and researchers.

        ### Want to learn more?

        - Github [GitHub](https://github.com/afugur)
        - Medium [Medium](https://medium.com/@afurkanugur05/creating-a-local-web-dashboard-for-a-monitored-building-de313ca67e51)
        - Linkedin  [Linkedin](https://www.linkedin.com/in/ahmet-furkan-u%C4%9Fur-730236205)

    """
    )


# Create Graph

def create_graph(data,col1,col2):
    # Create graph 1 using Plotly
    fig = go.Figure(data=go.Scatter(x=data[col1], y=data[col2], mode="lines", line_color="blue"))
    fig.update_layout(xaxis_title="Time (s)", yaxis_title="Acceleration (g)")
    st.plotly_chart(fig)

def disp_graph(data,col1,col2):
    # Create graph 1 using Plotly
    fig = go.Figure(data=go.Scatter(x=data[col1], y=data[col2], mode="lines", line_color="blue"))
    fig.update_layout(xaxis_title="Time (s)", yaxis_title="Displacement (cm)")
    max_value = abs(data[col2]).max()
    max_index = abs(data[col2]).idxmax()
    fig.add_annotation(x=data[col1][max_index], y=data[col2][max_index], text=f'Max: {round(data[col2][max_index],2)}', showarrow=True, arrowhead=1)
    st.plotly_chart(fig)
    st.write(f'Max Displacement: {round(data[col2][max_index],2)} cm')

def fft_graph(data,col1,col2,mod_freqs,threshold):

    i = 0

    fig = go.Figure(data=go.Scatter(x=data[col1], y=data[col2], mode="lines", line_color="blue"))
    fig.update_layout(xaxis_title="Frequency (hz)", yaxis_title="Amplitude")

    fig.add_shape(type="line", x0=data[col1].min(), x1=data[col1].max(), y0=max(data[col2])*threshold, y1=max(data[col2])*threshold,
                  line=dict(color="red", width=2, dash="dash"))

    for mod_freq in mod_freqs:
        i = i + 1
        mod_freq = round(mod_freq,2)
        fig.add_shape(type="line", x0=mod_freq, x1=mod_freq, y0=0, y1=data[col2].max(),
                      line=dict(color="green", width=2, dash="dash"))
        fig.add_annotation(x=mod_freq, y=data[col2].max(), text=f"{str(i)}.Mod {mod_freq} Hz",
                           showarrow=True, arrowhead=2, font=dict(color="green"))
    st.plotly_chart(fig)

#Download

def download_excel(df3):
    output = BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    df3.to_excel(writer,sheet_name="Results",  index=False)
    writer.close()
    output.seek(0)
    excel_data = output.read()
    b64 = base64.b64encode(excel_data)
    href = f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64.decode()}" download="data.xlsx">Download Excel file</a>'
    return href

# Global variables
acc_graph_data = None

class AccProcessing:

    def __init__(self):

        self.data = pd.DataFrame()

    def readData(self, path, sample_rate, count,format):
        if format == "txt":
            data = np.loadtxt(path, skiprows=1)
            self.data = pd.DataFrame(data*0.101972, columns=["Time", "Acc"])

        else:
                
            st = obspy.read(path)
            tr = st[0]
            
            data = tr.data / (9.81 * count)  # count to g
            data = data - np.mean(data)
    
            self.data["Time"] = tr.times()
            self.data["Acc"] = data

    def convertDisplacement(self):

        disp_df = pd.DataFrame()
        disp_data = intf(self.data["Acc"]*980.665, fs=1/self.data["Time"][1], times=2) # g to cm/s2 --> cm

        disp_data = disp_data - np.mean(disp_data)
        #disp_data = signal.detrend(disp_data,type="linear",bp=int(len(disp_data)/2))
        #disp_data_mean = np.mean(abs(disp_data))
        #disp_data[abs(disp_data) > disp_data_mean] = 0

        disp_df["Time"] = self.data["Time"]
        disp_df["Disp"] = disp_data

        return disp_df

    def fftProcess(self,windowing,overlap,threshold):

        mean_S = pd.DataFrame()

        M = windowing
        NFFT = M
        win = signal.windows.hamming(M)
        overlap = overlap
        overlap_samples = int(round(M*overlap)) # overlap in samples
        t, f, S = spectrogram(self.data["Acc"],fs=1/self.data["Time"][1],window=win,nperseg=M,noverlap=overlap_samples,nfft=NFFT)
    
        avg_S = np.mean(S,axis=1)
        mean_S["xf"] = t
        mean_S["fft"] = avg_S

        # Assuming you have the peak values stored in a NumPy array called 'peak_values'
        peak_indices, _ = find_peaks(mean_S["fft"].values, prominence=max(mean_S["fft"])*threshold)
        peak_indices = np.unique(peak_indices)
        mod_freqs = mean_S["xf"].values[peak_indices]

        return mean_S,mod_freqs


    def calculateDamping(self,mod_freqs,samples,overlap):

        results = pd.DataFrame()

        # half power
        half_df = dampHalf(self.data,mod_freqs,fs=1/self.data["Time"][1],samples=samples,overlap=overlap)
        log_df =  dampLog(self.data,mod_freqs,fs=1/self.data["Time"][1],samples=samples,overlap=overlap)

        data = {
            'Frequency (hz)': mod_freqs.flatten(),
            'Log (%)': log_df.values.flatten(),
            'Half (%)': half_df.values.flatten()
        }

        results = pd.DataFrame(data, index=[f'mod {i+1}' for i in range(len(mod_freqs))])
        results = results.round(2)

        return results

    def returnAccData(self):
        return self.data

acc_stuff = AccProcessing()

def mainPage():

    import streamlit as st

    st.title("Acceleration Value Processing Web Page")
    st.write("Enter details and upload file:")

    col1, col2 = st.columns([1, 1])
    with col1:
        sample_rate = st.number_input("Sample Rate", value=200, step=50)
    with col2:
        count = st.number_input("Count", value=318976, step=1)

    uploaded_file = st.file_uploader("Upload a file (.gcf, .mseed, .txt, etc.)")
    file_format = None

    read_clicked = st.button("Start Read")

    # Acceleration Graph
    st.subheader("Acceleration - Time")

    if uploaded_file is not None:
        file_name, file_extension = os.path.splitext(uploaded_file.name)
        file_extension = file_extension.lower()
        st.write("Debug1:", file_extension)
        if file_extension == ".txt":
            file_format = "txt"
        elif file_extension == ".gcf":
            file_format = "gcf"
        elif file_extension == ".mseed":
            file_format = "mseed"
        else:
            st.warning("Unsupported file format. Supported formats: .txt, .gcf, .mseed")


        global acc_stuff,acc_graph_data
        acc_stuff = AccProcessing()
        st.write("Debug2:", uploaded_file)
        acc_stuff.readData(uploaded_file, sample_rate, count,file_format)
        data = acc_stuff.returnAccData()
        
        create_graph(data,"Time","Acc")

        acc_graph_data = data.copy()


    # First graph
    if acc_graph_data is not None and acc_stuff is not None:

        # Analysis Section
        st.header("Analysis")
        st.subheader("Analysis Settings")

        # Analysis Settings
        st.write("Enter Analysis Settings and Start Analysis:")
        col1, col2, col3 = st.columns([1, 1, 1])
        with col1:
            windowing = st.number_input("Windowing", value=1024, step=256)
        with col2:
            overlap = st.number_input("Overlap (%)", value=0.66, step=0.1)
        with col3:
            threshold = st.number_input("Threshold", value=66, step=1)

        analyze_clicked = st.button("Start Analyze")
        st.subheader("Displacement - Time")
        # Button for calculating other graphs
        if analyze_clicked:
            if acc_graph_data is not None:
                disp_df = acc_stuff.convertDisplacement()
                disp_graph(disp_df,"Time","Disp")

                st.subheader("Frequency - Amplitude")
                mean_df,mod_freqs = acc_stuff.fftProcess(windowing,overlap,threshold/100)

                if mod_freqs.size == 0:
                    message = "Reduce Threshold Try Again"
                    st.warning(message)

                else:

                    fft_graph(mean_df,"xf","fft",mod_freqs,threshold/100)

                    results = acc_stuff.calculateDamping(mod_freqs,windowing,overlap)

                    st.subheader("Results")

                    st.write(results)

                    st.markdown(download_excel(results), unsafe_allow_html=True)




if __name__ == "__main__":
    st.set_page_config(
        page_title="Streamlit App",
        page_icon=":rocket:",
        layout="wide"
    )

    page_names_to_funcs = {

    "Read Acceleration Page": mainPage,
    "About Me": intro,

    
    }

    demo_name = st.sidebar.selectbox("Select a Page", page_names_to_funcs.keys())
    page_names_to_funcs[demo_name]()
    # Streamlit uygulamanızın çağrıldığı yerdeki fonksiyonu buraya ekleyin
