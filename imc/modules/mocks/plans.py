mock_plan_case_1 = """
Taking into account this API schema:
__SCHEMA__
Use the API as follows:
1. Check all the orders, find the one afected and save the field product id (productID) related to that order and save the field Work order id (workOrderID).
2. Search for that product id to get the details. From the components and materials, get the component id or material id afected (materialID or componentID).
3. Seacrh for all the suppliers that can provide that material or component using the material id or component id and the Work order id to get the actual supplier and the potential suppplier. ((materialID or componentID) and workOrderID) 

Once you get all the data, propose the best potenial supplier to prevent disruptions.
"""

mock_plan_case_2 = """
Use the context retrieved from the rag tool to answer the questions related to machine maintences.
Give clear and complete response, and do not skip any step of the proces. 
It is critical that you stick to the content of the context received.
"""