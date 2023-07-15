import streamlit as st
from dotenv import load_dotenv; load_dotenv()
import httpx
import os

# Parse comma separated user:pass pairs from env var
CREDS = [tuple(userpass.split(':')) for userpass in os.environ['CREDS'].split(',')]
RUNPOD_POD_ID = os.environ['RUNPOD_POD_ID']
RUNPOD_API_KEY = os.environ['RUNPOD_API_KEY']
RUNPOD_POD_GPUS = int(os.environ['RUNPOD_POD_GPUS'])
auth_params = {'api_key': RUNPOD_API_KEY}

def get_pod_info(pod_id: str):
    data = {
        "query": f'query Pod {{ pod(input: {{podId: "{pod_id}"}}) {{ id name runtime {{ uptimeInSeconds ports {{ ip isIpPublic privatePort publicPort type }} gpus {{ id gpuUtilPercent memoryUtilPercent }} container {{ cpuPercent memoryPercent }} }} }} }}'
    }

    resp = httpx.post('https://api.runpod.io/graphql', params=auth_params, json=data)
    resp.raise_for_status()
    return resp.json()


def start_pod(pod_id: str, gpu_count: int):
    mutation = f"""
    mutation {{
        podResume(input: {{podId: "{pod_id}", gpuCount: {gpu_count}}}) {{
            id, desiredStatus, imageName, env, machineId, machine {{ podHostId }}
        }}
    }}
    """
    data = {'query': mutation}
    resp = httpx.post('https://api.runpod.io/graphql', params=auth_params, json=data)
    resp.raise_for_status()
    return resp.json()


def stop_pod(pod_id: str):
    # {"query": "mutation { podStop(input: {podId: \"riixlu8oclhp\"}) { id desiredStatus } }"}'
    mutation = f"""
    mutation {{ podStop(input: {{podId: "{pod_id}"}}) {{ id desiredStatus }} }}
    """
    data = {'query': mutation}
    resp = httpx.post('https://api.runpod.io/graphql', params=auth_params, json=data)
    resp.raise_for_status()
    return resp.json()


def display_pod_info(pod_info: dict):
    # TODO: Add display of current account credit (https://graphql-spec.runpod.io)
    # TODO: Add display of current users connected to the pod
    # TODO: Per-GPU memory usage.
    # TODO: Nice display, html+css? Gotta be some way to integrate with stremalit...

    pod_info = pod_info['data']['pod']
    status = 'ON' if pod_info.get('runtime') else 'OFF'  # assuming the runtime field is null when the machine is off
    st.write(f'Pod status: {status}')

    if status == 'ON':
        st.write(f'Memory Usage: {pod_info["runtime"]["container"]["memoryPercent"]}%')
        st.write(f'CPU Usage: {pod_info["runtime"]["container"]["cpuPercent"]}%')
        st.write(f'GPU Memory Usage: {pod_info["runtime"]["gpus"][0]["memoryUtilPercent"]}%')

        # Show ssh command
        st.write('SSH command:')
        for port in pod_info['runtime']['ports']:
            if port['privatePort'] == 22 and port['isIpPublic']:
                st.code(f'ssh root@{port["ip"]} -p {port["publicPort"]} -i ~/.ssh/id_ed25519')
        st.write("(Private key can be found [here](https://serialignment-qo78019.slack.com/archives/C0523R9M58C/p1689396107110739?thread_ts=1689392014.184409&cid=C0523R9M58C) on slack.)")


def main():
    st.title('Sharder')
    st.image('./shard-mouse-logo.webp', width=200)

    username = st.sidebar.text_input("User Name", value="", type="default")
    password = st.sidebar.text_input("Password", value="", type="password")
    session_state = st.session_state

    if 'is_logged' not in session_state:
        session_state.is_logged = False

    if (username, password) in CREDS:
        session_state.is_logged = True

    if session_state.is_logged:
        st.success('Logged in successfully')

        st.header("Pod info")
        if st.button('Refresh pod info'):
            st.success('Refreshed Pod Info')
            pod_info = get_pod_info(RUNPOD_POD_ID)
            display_pod_info(pod_info)
        else:
            pod_info = get_pod_info(RUNPOD_POD_ID)
            display_pod_info(pod_info)


        def handle_response(res, action):
            if res.get('errors'):
                st.error(f'Failed to {action} pod.')
                st.write("Errors:", res['errors'])
            else:
                st.success(f'Pod {action} request successfully sent.')


        # Start pod button
        st.header('Pod controls')
        if st.button('Start pod'):
            res = start_pod(RUNPOD_POD_ID, RUNPOD_POD_GPUS)
            handle_response(res, "start")
        if st.button("Stop pod"):
            res = stop_pod(RUNPOD_POD_ID)
            handle_response(res, "stop")
    else:
        st.warning('Please enter valid credentials through the sidebar.')


if __name__ == '__main__':
    main()
