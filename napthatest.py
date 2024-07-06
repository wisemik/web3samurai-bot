import asyncio
from naptha_sdk.client.naptha import Naptha
from naptha_sdk.client.node import Node
from naptha_sdk.task import Task
from naptha_sdk.flow import Flow
from naptha_sdk.user import generate_user
import os


async def main():
  naptha = await Naptha(
      user=generate_user()[0],
      hub_username=os.getenv("HUB_USER"),
      hub_password=os.getenv("HUB_PASS"),
      hub_url="ws://node.naptha.ai:3001/rpc",
      node_url="http://node.naptha.ai:7001",
      routing_url=os.getenv("ROUTING_URL"),
      indirect_node_id=os.getenv("INDIRECT_NODE_ID")
  )

  flow_inputs = {"prompt": 'i would like to count up to ten, one number at a time. ill start. one.'}
  worker_nodes = [Node("http://node.naptha.ai:7001"), Node("http://node1.naptha.ai:7001")]

  flow = Flow(name="multiplayer_chat", user_id=naptha.user["id"], worker_nodes=worker_nodes, module_params=flow_inputs)

  task1 = Task(name="chat_initiator", fn="chat", worker_node=worker_nodes[0], orchestrator_node=naptha.node, flow_run=flow.flow_run)
  task2 = Task(name="chat_receiver", fn="chat", worker_node=worker_nodes[1], orchestrator_node=naptha.node, flow_run=flow.flow_run)

  response = await task1(prompt=flow_inputs["prompt"])

  for i in range(10):
      response = await task2(prompt=response)
      response = await task1(prompt=response)

if __name__ == "__main__":
    asyncio.run(main())
