# API

_Gegenereerd door docsnap-v2_

---

## Store non-order-related Task in Ride - Informatie voor ontwikkelaars - MendriX Support & Documentatie

_Bron: https://support.mendrix.nl/space/API/1523941386/Store+non-order-related+Task+in+Ride_

# Store non-order-related Task in Ride

The `TEoCustomLinkRideNonOrderTask` type defines the structure used to store non-order-related tasks within a ride via Custom Link. These tasks can include actions such as linking, unlinking, breaks, or rest periods during a ride.

After adding linking/unlinking task in the ride, it will also update the trailer id(Material1) for all the follow-up tasks.

Below is an overview of the store request, the response, and their respective attributes:

```xml
<?xml version="1.0" encoding="windows-1252"?>
<EoCustomLinkStoreRideNonOrderTask Type="TEoCustomLinkStoreRideNonOrderTask" xsi:noNamespaceSchemaLocation="GdxEoStructures.xsd" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
    <Data Type="TEoCustomLinkRideNonOrderTask">
        <AfterTaskId>0</AfterTaskId>
        <BeforeTaskId>0</BeforeTaskId>
        <Id>-1</Id>
        <TaskTypeId>7</TaskTypeId>
        <RideId>107</RideId>
        <Address Type="TEoAddress">
            <Name>Citroen Janssen</Name>
            <Premise>Premise1</Premise>
            <Street>De Jonghstraat 4</Street>
            <Number/>
            <PostalCode>5461 HD</PostalCode>
            <Place>Veghel</Place>
            <Country>Nederland</Country>
        </Address>
        <MaterialId>4</MaterialId>
        <MaterialNumber>73-MK-NO1</MaterialNumber>
        <HandlingTimeInMinutes>10</HandlingTimeInMinutes>
    </Data>
</EoCustomLinkStoreRideNonOrderTask>
```

## Attributes:

1. **AfterTaskId** (optional):
   - **Type**: `TNullableInteger`
   - **Description**: AfterTaskId is the task id after which this task will be placed. If both AfterTaskId and BeforeTaskId are 0, the task will be added at the beginning of the ride.

2. **BeforeTaskId** (optional):
   - **Type**: `TNullableInteger`
   - **Description**: BeforeTaskId is the task id before which this task will be placed. If this field and AfterTaskId are 0, the task will be added at the beginning of the ride..

3. **Id** (Optional):
   - **Type**: `TNullableInteger`
   - **Description**: The unique identifier of the non-order-related task. If the value is less than or equal to zero, the task will be added to MendriX. Otherwise, it will update an existing non-order-related task.

4. **TaskTypeId** (Mandatory):
   - **Type**: `TNullableInteger`
   - **Description**: The type of task. It must be one of the following:
     - 7: Linking (Task type id for this is 7).
     - 8: Unlinking (Task type id for this is 8).
     - 9: Break (Task type id for this is 9).
     - 10: Rest (Task type id for this is 10).

5. **RideId** (Mandatory):
   - **Type**: `TNullableInteger`
   - **Description**: The ride id associated with the task. It is required and must exist in MendriX when inserting or updating the task.

6. **Address** (optional):
   - **Type**: `TEoAddress`
   - **Description**: The address associated with the task. It includes details such as name, premise, street, postal code, place, and country.

7. **MaterialId** (optional):
   - **Type**: `TNullableInteger`
   - **Description**: The id of the material/trailer associated with the linking task. Flag IsMaterial should enable in MendriX.

8. **MaterialNumber**
   a. Type: TNullableString
   b. Description:Alternative identifier for the material associated with the task. When both MaterialId and MaterialNumber are provided, the MendriX will use MaterialId and ignore MaterialNumber. Flag IsMaterial should enable in MendriX.

9. **HandlingTimeInMinutes** (optional):
   - **Type**: `TNullableInteger`
   - **Description**: The handling time for the task, in minutes.

**Success response to store request**

```xml
<?xml version="1.0" encoding="windows-1252"?>
<EoStoreResultList Type="TEoStoreResultList">
	<_TEoListBase_Items>
		<EoStoreResult Type="TEoStoreResult">
			<Id>356</Id>
			<IdOld>-1</IdOld>
			<RowsAffected>1</RowsAffected>
			<StoreDescription/>
			<StoreDetail>0</StoreDetail>
			<StoreResult>srUpdated</StoreResult>
			<ErrorType>etNone</ErrorType>
		</EoStoreResult>
	</_TEoListBase_Items>
</EoStoreResultList>
```

**Validation failure (e.g., Database Error):**

```xml
<?xml version="1.0" encoding="windows-1252"?>
<EoStoreResultList Type="TEoStoreResultList">
    <_TEoListBase_Items>
        <EoStoreResult Type="TEoStoreResult">
            <Id>360</Id>
            <IdOld>0</IdOld>
            <RowsAffected>0</RowsAffected>
            <StoreDescription>EDatabaseError:DBMessage;</StoreDescription>
            <StoreDetail>0</StoreDetail>
            <StoreResult>srError</StoreResult>
            <ErrorType>etUnknown</ErrorType>
        </EoStoreResult>
    </_TEoListBase_Items>
</EoStoreResultList>
```

**Input data validation failure**

```xml
<?xml version="1.0" encoding="windows-1252"?>
<EoCustomLinkException Type="TEoCustomLinkException">
	<ExceptionClassName>Exception</ExceptionClassName>
	<ExceptionMessage>RideId is required and must be provided.</ExceptionMessage>
</EoCustomLinkException>
```

Here are other input data validation errors,

- RideId is required and must be provided.
- TaskTypeId should be one of the following: linking, unlinking, break, or rest.
- Ride not found.
- Unable to update task because it is not present in the ride.
- Unable to edit because the task is not non order related.
- After or Before task not found in the ride.
- MaterialNumber <MaterialNumber> not found.
- MaterialId <MaterialId> not found.

**XML structure or data type error**

```xml
<?xml version="1.0" encoding="windows-1252"?>
<EoCustomLinkException Type="TEoCustomLinkException">
    <ExceptionClassName>EConvertError</ExceptionClassName>
    <ExceptionMessage>
        Failed /TEoCustomLinkStoreOrdersNormal/ @ UEoBase.MakeEoCoreFromObjectXml(), 
        XML: /&lt;?xml version=&quot;1.0&quot; encoding=&quot;windows-1252&quot;?&gt;
        &lt;EoCustomLinkStoreOrdersNormal Type=&quot;TEoCustomLinkStoreOrdersNormal&quot; 
        xsi:noNamespaceSchemaLocation=&quot;GdxEoStructures.xsd&quot; xmlns:xsi=&quot;http://www.w3.org/200/&gt;
        
        Inner: 
        Failed field: /Longitude/ := /sd/ @ TRTTIEnabler.SetValue()
        
        Inner: 
        &apos;sd&apos; is not a valid floating point value
    </ExceptionMessage>
</EoCustomLinkException>
```

---

## Store Package Transactions - Informatie voor ontwikkelaars - MendriX Support & Documentatie

_Bron: https://support.mendrix.nl/space/API/479133697/Store+Package+Transactions_

# Store Package Transactions

This command can be used to store package transactions for a specific task or good.

## Request

```xml
<?xml version="1.0" encoding="windows-1252"?>
<EoCustomLinkStorePackageTransactions Type="TEoCustomLinkStorePackageTransactions" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="GdxEoStructures.xsd">
    <Data Type="TEoCustomLinkPackageTransactionList">
        <_TEoListBase_Items>
            <EoCustomLinkPackageTransaction Type="TEoCustomLinkPackageTransaction">
                <GoodId>429</GoodId>
                <TaskId>0</TaskId>
                <TransferIn>5</TransferIn>
                <TransferOut>3</TransferOut>
                <PackingId>6</PackingId>
            </EoCustomLinkPackageTransaction>
        </_TEoListBase_Items>
    </Data>
</EoCustomLinkStorePackageTransactions>
```

The elements `<TaskId>` and `<GoodId>` are optional but at least one of them has to be specified. In the above example request, `<TaskId>` has been set to zero to indicate it should not be used. You can also achieve this by leaving `<TaskId>` out of the request.

The element `<TransferIn>` specifies the number of packagings retrieved, while `<TransferOut>` sets the number of packagings unloaded.

## Response

### Success response

```xml
<?xml version="1.0" encoding="windows-1252"?>
<EoStoreResultList Type="TEoStoreResultList">
    <_TEoListBase_Items>
        <EoStoreResult Type="TEoStoreResult">
            <Id>230</Id>
            <IdOld>230</IdOld>
            <RowsAffected>1</RowsAffected>
            <StoreDescription/>
            <StoreDetail>0</StoreDetail>
            <StoreResult>srUpdated</StoreResult>
            <ErrorType>etNone</ErrorType>
        </EoStoreResult>
    </_TEoListBase_Items>
</EoStoreResultList>
```

The returned `<Id>` refers to the order to which the task or good belongs.

### Error response

```xml
<?xml version="1.0" encoding="windows-1252"?>
<EoStoreResultList Type="TEoStoreResultList">
    <_TEoListBase_Items>
        <EoStoreResult Type="TEoStoreResult">
            <Id>0</Id>
            <IdOld>0</IdOld>
            <RowsAffected>0</RowsAffected>
            <StoreDescription>One or more values are invalid: PackingId [123], TaskId [566] and/or GoodId [-1]</StoreDescription>
            <StoreDetail>0</StoreDetail>
            <StoreResult>srError</StoreResult>
            <ErrorType>etNone</ErrorType>
        </EoStoreResult>
    </_TEoListBase_Items>
</EoStoreResultList>
```

The `<StoreDescription>` describes the (possible) causes of an error.

---

## Request Questionnaire Question-Answer Pairs - Informatie voor ontwikkelaars - MendriX Support & Documentatie

_Bron: https://support.mendrix.nl/space/API/479461535/Request+Questionnaire+Question-Answer+Pairs_

# Request Questionnaire Question-Answer Pairs

## How To Request Questionnaire Question-Answer Pairs By TaskId

Requesting Questionnaire Question-Answer pairs from MendriX TMS can be done using the following steps.

> For other (important) information, always read [Getting Started](/space/API/93881066) first.

## Step 1 - Connect

Connect module Custom Link.

## Step 2 - Request Data Questionnaire Question-Answer Pairs

Next send the request to retrieve Question-Answer Pairs for given TaskId(s).

```xml
<?xml version="1.0" encoding="windows-1252"?>
<EoCustomLinkRequestQuestionnaireAnswers Type="TEoCustomLinkRequestQuestionnaireAnswers" xsi:noNamespaceSchemaLocation="GdxEoStructures.xsd" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
<Nested>False</Nested>
<Filter Type="TEoFilterQuestionnaireAnswers">
<TaskIdsCsv>2219,2220</TaskIdsCsv>
</Filter>
</EoCustomLinkRequestQuestionnaireAnswers>
```

## Step 3 - Receive Response

Receive the response containing the XML of the matching questionnaires. Each questionnaire has the TaskId and XML.

```xml
<?xml version="1.0" encoding="windows-1252"?>
<EoCustomLinkResponseQuestionnaireAnswers Type="TEoCustomLinkResponseQuestionnaireAnswers">
    <Data Type="TEoCustomLinkQuestionnaireAnswerList">
        <_TEoListBase_Items>
            <EoCustomLinkQuestionnaireAnswer Type="TEoCustomLinkQuestionnaireAnswer">
                <QuestionnaireId>2</QuestionnaireId>
                <Moment>2001-11-09T10:28:22+01:00</Moment>
                <GoodId>917</GoodId>
                <TaskId>2219</TaskId>
                <QuestionId>6</QuestionId>
                <QuestionKey>Payment_COD</QuestionKey>
                <Question>Is de rembours volledig voldaan?</Question>
                <AnswerId>5</AnswerId>
                <AnswerIndex>0</AnswerIndex>
                <AnswerType>Select</AnswerType>
                <AnswerValues>[0]</AnswerValues>
            </EoCustomLinkQuestionnaireAnswer>
        </_TEoListBase_Items>
    </Data>
</EoCustomLinkResponseQuestionnaireAnswers>
```

## Step 4 - Disconnect

Disconnect module Custom Link.

```
\Bin\Metadata\EoCustomLinkRequestQuestionnaireAnswers.xml
\Bin\Metadata\EoCustomLinkResponseQuestionnaireAnswers.xml
```

---

## Request Last Positions of Rides - Informatie voor ontwikkelaars - MendriX Support & Documentatie

_Bron: https://support.mendrix.nl/space/API/511705089/Request+Last+Positions+of+Rides_

# Request Last Positions of Rides

## Steps

It is possible to request the last position for rides from Custom Link which match specified criteria. The following files contain examples of a request and a response.

- Connect module Custom Link.
- Send a EoCustomLinkRequestLastRidePositions XML request.
- Receive the EoCustomLinkResponseLastRidePositions XML response.
- Disconnect module Custom Link

> For other (important) information, always read [Getting Started](/space/API/93881066) first.

## Example Files

| |
|---|
| `\Bin\Metadata\EoCustomLinkRequestLastRidePositions.xml` |
| `\Bin\Metadata\EoCustomLinkResponseLastRidePositions.xml` |

---

## Authentication - Informatie voor ontwikkelaars - MendriX Support & Documentatie

_Bron: https://support.mendrix.nl/space/API/616988673/Authentication_

# Authentication

## Custom Link - API Tokens

To authenticate yourself in Custom Link using SOAP, you will need an API token. These can be generated as described below in **API Tokens**.

> To use the API token, fill it in as your username and leave the password field blank, unless the token representation you chose is as a username and password combination.

[Use SOAP to connect | Example-SOAP-header](/space/API/93881111/Use+SOAP+to+connect#Example-SOAP-header)

## API tokens

The screen to manage the API tokens can be found under:
`Bestand` | `Opties` | `Koppelingen` | `Custom Link` | `API Tokens`.
It is only possible to manage these tokens when the user has the permission `API tokens beheren`.

To create a new API token, click on the plus icon. You will then be asked what kind of API token you'd like to make. This affects the scope of the token, so pick carefully.

If you choose to create a token for a single client (first option), a dialog pops up asking you for which client you would like to create this token. If you choose to create a token for access to all data (second option), this token will give you access to the data of all clients and more. After that, you can give a label to the token, so it's easier to find it later on.

> The second option will **show data of more than one customer**. Mostly this is used for connections to WMS and ERP like software internal for the customer of MendriX.

You will also have the choice of the token representation. The top option (default) will result in a single token that you'll need to use as a username when making the SOAP request. When the second option is chosen, a username and password combination is generated that can be used when making the request.

> **The token will only be shown once.** So note this token somewhere safe. When the token is lost, you will have to create a new token.

The token can then be used to log in into [Custom Link](#Custom-Link).
It is possible to change the label of a token on a later date. This can be done by selecting the token in the list and then clicking on the pen icon on the right.

Tokens do not expire while they exist. To revoke a token, the token must be deleted. After deletion, it is no longer possible to use the token to login into Custom Link.

If a token is made to access all data, it is possible to log in using that token for authorization. Check the wiki of our [API definition](https://mendrix.atlassian.net/wiki/spaces/MAD) on where to find the login endpoints.

> Token deletion is permanent and cannot be undone.

> It is not possible to edit API tokens when MendriX has been started in archive mode.

---

## MendriX XML structure: Create a new order - Informatie voor ontwikkelaars - MendriX Support & Documentatie

_Bron: https://support.mendrix.nl/space/API/689831937/MendriX+XML+structure:+Create+a+new+order_

# MendriX XML structure: Create a new order

On this page the basic structure of MendriX Orders are explained as well as how to create a new MendriX order. On the [Create Orders page](https://wiki.mendrix.nl/space/API/93881082/Create+Orders#How-to-create-a-(simple)-new-order), an order structure can be found, as well as some more in depth informations regarding some of the variables that can be used.

## Basis structure of the MendriX XML

The XML command to create a new order consists of the following tags:

- EoCustomLinkStoreOrderNormal

- EoOrderMx
- EoGoodMx
- EoTask 
- EoGoodToTaskMx

These tags, their relationship and variables will be discussed below. The details in the tag are that of a simple order with one good and one task. To add more information and specific variables, the GDXStructures file needs to be consulted to find the desired field. This file can be requested by contacting MendriX support or your MendriX consultant.

## EoCustomLinkStoreOrderNormal tag

To enter a new order, you must construct a valid XML-command. This main tag for this XML-command is the EoCustomLinkStoreOrderNormal-tag

The EoCustomLinkStoreOrderNormal-tag should contain only one order.

```
<?xml version="1.0" encoding="windows-1252"?>
<EoCustomLinkStoreOrdersNormal Type="TEoCustomLinkStoreOrdersNormal"   xsi:noNamespaceSchemaLocation="GdxEoStructures.xsd" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
            <Data Type="TEoOrderMxList">
                        <_TeoListBase_Items>
                        <EoOrderMx Type="TEoOrderMx">
                        ....
                        </EoOrderMx>
                        </_TeoListBase_Items>
            </Data>
</EoCustomLinkStoreOrdersNormal>
```

## EoOrderMx tag

Each EoOrderMx-tag contains the information with regard to the order, a list of goods ("TEoGoodMxList") that need to be transported and a list assigning the goods to specific tasks ("TEoGoodToTaskMxList"). Each new order should be created with a **negative ID**, in that way, MendriX will generate the next, unique order ID for the order.

The red variables below should be filled in with client/relation specific details.

```
<EoOrderMx Type="TEoOrderMx">
  <OrderId Type="TEoKeyIntInfraMx">
    <Id>-1000</Id>
  </OrderId>
  <ClientId Type="TEoKeyIntInfraMx">
    <Id>110</Id>
  </ClientId>
  <Contact>Hr. Kwartel</Contact>
  <Moment>2023-06-20T17:00:00</Moment>
  <ProductId Type="TEoKeyIntInfraMx">
    <Id>1</Id>
  </ProductId>
  <Reference>Orderreference</Reference>
  <ExternalDone>True</ExternalDone>
  <ExternalSource>191</ExternalSource>
  <Goods Type="TEoGoodMxList">
    <_TeoListBase_Items>
      <EoGoodMx Type="TEoGoodMx">
      ...
      </EoGoodMx>
    </_TeoListBase_Items>
  </Goods>
  <Tasks Type="TEoTaskMxList">
    <_TeoListBase_Items>
      <EoTaskMx Type="TEoTaskMx">
      ...
      </EoTaskMx>
    </_TeoListBase_Items>
  </Tasks>
  <GoodsToTasks Type="TEoGoodToTaskMxList">
    <_TeoListBase_Items>
      <EoGoodToTaskMx Type="TEoGoodToTaskMx">
    ...
     </EoGoodToTaskMx>
    </_TeoListBase_Items>
  </GoodsToTasks>
</EoOrderMx>
```

## EoGoodMx - tag

Each EoGoodMx-tag describes the goods to be delivered. Each good must have an unique **negative GoodId**. The red tags should be specified with your variables. When more goods are added you have to repeat the EoGoodMx-tag. Each should contain a **new, unique negative GoodId** (-2, -3 etc.).

```
<EoGoodMx Type="TEoGoodMx">
  <GoodId Type="TEoKeyIntInfraMx">
    <Id>-1</Id>
  </GoodId>
  <Packing Type="TEoPackingMx">
    <Name>enveloppen</Name>
  </Packing>
  <Comments>lood</Comments>
  <Width>0.0</Width>
  <Barcode>63ff5e13028a6</Barcode>
  <Depth>0.0</Depth>
  <Height>0.0</Height>
  <Parts>1</Parts>
  <Weight>15.0</Weight>
  <Volume>0.0</Volume>
  <VolumeWeight>0.0</VolumeWeight>
  <ArticleWeight>0.0</ArticleWeight>
</EoGoodMx>
```

## EoTaskMx

For the activites that need to be executed, a task should be created. An order can contain more than one task. Each task must have a different **negative TaskId**, in order to create a new, unique task database number.

The Type of task that is created is determined by the field <TasktypeId>. A standard loading task has ID 1, unloading is ID 2. For custom ID's and task, the database key of the task in MendriX should be consulted.

```
<EoTaskMx Type="TEoTaskMx">
  <TaskId Type="TEoKeyIntInfraMx">
       <Id>-100</Id>
  </TaskId>
  <TaskTypeId Type="TEoKeyIntInfraMx">
       <Id>1</Id>
  </TaskTypeId>
  <Address Type="TEoAddress">
    <Name>Bloembol Sjaak</Name>
    <Premise>Kwartel</Premise>
    <Street>De Jonghstraat 4</Street>
    <Number></Number>
    <PostalCode>5461 HD</PostalCode>
    <Place>Veghel</Place>
    <State></State>
    <Country>Nederland</Country>
    <CountryCode>NL</CountryCode>
  </Address>
  <Connectivity Type="TEoConnectivity">
    <Email></Email>
    <Fax></Fax>
    <Mobile></Mobile>
    <Phone>0413-556623</Phone>
    <Web></Web>
  </Connectivity>
  <ContactName>Sjaak Loebstra</ContactName>
  <Instructions>Trek gele Uniqo-jas aan!</Instructions>
  <HandlingTimeInMinutes>115</HandlingTimeInMinutes>
  <Requested Type="TEoDateTimeWindow">
    <DateTimeEnd>2023-07-01T10:00:00</DateTimeEnd>
    <DateTimeBegin>2023-07-01T10:00:00</DateTimeBegin>
  </Requested>
  <ReferenceOur>Reference Our</ReferenceOur>
  <ReferenceYour>Reference Your </ReferenceYour>
</EoTaskMx>
```

### EoGoodToTaskMx

The EoGoodToTaskMx-tag is required to link the specified goods to the corresponding tasks. Here you must specify the **negative task** and **good id's** to connect them both. Each EoGoodToTaskMx connects **ONE** good to **ONE** task.

```
<EoGoodToTaskMx Type="TEoGoodToTaskMx">
  <GoodId Type="TEoKeyIntInfraMx">
       <Id>-1</Id>
  </GoodId>
  <TaskId Type="TEoKeyIntInfraMx">
       <Id>-100</Id>
  </TaskId>
</EoGoodToTaskMx>

<EoGoodToTaskMx Type="TEoGoodToTaskMx">
     <GoodId Type="TEoKeyIntInfraMx">
             <Id>-2</Id>
      </GoodId>
      <TaskId Type="TEoKeyIntInfraMx">
             <Id>-100</Id>
        </TaskId>
</EoGoodToTaskMx>
```

## XML result EoCustomLinkStoreOrderNormal

After the order is created successfully, you receive an XML response, which contains the Id of the created order.

```
<?xml version="1.0" encoding="windows-1252"?>
            <EoStoreResultList Type="TEoStoreResultList">
                        <_TeoListBase_Items>
                                    <EoStoreResult Type="TEoStoreResult">
                                    <Id>11431</Id>
                                    <IdOld>-1000</IdOld>
                                    <RowsAffected>1</RowsAffected>
                                    <StoreDescription></StoreDescription>
                                    <StoreDetail>0</StoreDetail>
                                    <StoreResult>srInserted</StoreResult>
                                    <StoreResult>srInserted</StoreResult>
                                    <ErrorType>etNone</ErrorType>
                        </EoStoreResult>
            </_TeoListBase_Items>
</EoStoreResultList>
```

---

## Custom Link en Updates - Informatie voor ontwikkelaars - MendriX Support & Documentatie

_Bron: https://support.mendrix.nl/space/API/93880718/Custom+Link+en+Updates_

# Custom Link en Updates

## Introductie

Bij het uitvoeren van een update, adviseren wij om eerst deze update op een test-omgeving te installeren en deze uitvoerig te testen. Dit is vooral het geval als u koppelingen gebruikt die verbinden met module Custom Link. Het is van belang dat het testen van de update en de koppelingen goed verlopen. Indien u een testomgeving wilt inrichten, verstrekt Mendrix na aanvraag gratis een licentie voor deze testomgeving.

## Updaten productie-omgeving

Als op de testomgeving na de update de testen goed verlopen zijn en de koppelingen goed blijven werken, kan de update worden uitgevoerd op de productie-omgeving. U dient zélf zeker te stellen dat de koppelingen blijven werken na deze update. Twijfelt u toch? Voer dan de installatie van deze update NIET uit, en neem contact op met MendriX. Lees voor verdere info betreft updates de pagina [Installatie van MendriX TMS](/space/TMS/93880775)

---

## Getting Started - Informatie voor ontwikkelaars - MendriX Support & Documentatie

_Bron: https://support.mendrix.nl/space/API/93881066/Getting+Started_

# Getting Started

The default way to communicate with [MendriX TMS](/space/TMS/93880728) is with XML or [SOAP](/space/API/93881111) through the so called module Custom Link. Here you can find all information you need to develop your own middleware. In addition to these articles, the latest supporting SDK files are always installed with the latest MendriX TMS in the folder *\Bin\Metadata*. In this folder you will find example XML, the latest XSD and DemoCustomLink.exe tool, with which tests kan be performed and to which are referred in this Wiki.

## Getting Started

Communicating with module Custom Link is quite simple. For each request, follow the next steps:

- First you create a connection with module Custom Link.
- Then you send a XML request through that connection.
- After processing a XML response will be send back to you.
- You may now:
  - **or you may send multiple new commands over the same connection** (serialized) and having a lot of speed benefit (up to 6x-10x more speed has been measurement using this method)
  - **or you may close the connection and reconnect for a new command**, this prevents the need to detect a disconnection and setting up a new connection only when needed, but this method maybe 6x-10x slower then re-using the connection

That's it!

Now read on for the [important basics](/space/API/93881105) and then you are ready for sending your first command.

## Important Basics

[Read the basics first](/space/API/93881105) about connecting module Custom Link, the proper XML and other basics. This should be enough to get you going and let you implement full two-way synchronisation between an external system and module Custom Link of the MendriX TMS.

## Sending Your First Command

Now that you read all of the basics, we recommend you start communicating with module Custom Link with the simplest command that exists, which is requesting the current date and time. See [Requesting the current Date and Time](/space/API/93881096)

## List of All Commands

- [Activate Order Template](/space/API/93881099)
- [Change Clients](/space/API/93881102)
- [Change Employees](/space/API/93881101)
- [Change Orders](/space/API/93881088)
- [Create Clients](/space/API/93881089)
- [Create Employees](/space/API/93881097)
- [Create Hours](/space/API/93881070)
- [Create memos](/space/API/93881087)
- [Create Orders](/space/API/93881082)
- [Create Traces](/space/API/93881083)
- [Increase Id's](/space/API/93881086)
- [Keep Alive](/space/API/93881103)
- [Request​ Distances](/space/API/93881076)
- [Request Client by Id](/space/API/93881077)
- [Request Employees](/space/API/93881095)
- [Request Hours](/space/API/93881085)
- [Request Invoices](/space/API/93881091)
- [Request Job by Id](/space/API/93881072)
- [Request Job Id's](/space/API/93881081)
- [Request Job Progress](/space/API/93881093)
- [Request Order by Id](/space/API/93881100)
- [Request Order Id's](/space/API/93881074)
- [Request Packaging Transactions](/space/API/93881075)
- [Request Questionnaire by TaskId](/space/API/93881090)
- [Request Questionnaire Question-Answer Pairs](/space/API/479461535)
- [Request Rides (compact)](/space/API/93881092)
- [Request Traces](/space/API/93881069)
- [Requesting Date+Time](/space/API/93881096)
- [Store Job Completed](/space/API/93881080)
- [Store Job Progress](/space/API/93881078)
- [Store Measurement](/space/API/93881098)
- [Store Orderimport Status](/space/API/93881079)
- [Store Ride](/space/API/93881073)
- [Store Ride Timewindow](/space/API/93881094)
- [Store Package Transactions](/space/API/479133697)

## In Depth Technical

Don't forget to read the [technical details](/space/API/93881104) (especially about Server Load, Encoding, Compatibility and Communication).

## Disclaimer

This and other documentation concerning the product MendriX and it's technology, and the provided XML and XSD documents, do not provide any grounds for legal demands or grounds for claims. It is purely informative and contains preliminary information. It is subject to future changes and corrections. Discrepancies with reality will be corrected after being passed on.

---

## Commands - Informatie voor ontwikkelaars - MendriX Support & Documentatie

_Bron: https://support.mendrix.nl/space/API/93881068/Commands_

# Commands

Please read [Getting Started](/space/API/93881066) first.

- [Activate Order Template](/space/API/93881099)
- [Change Clients](/space/API/93881102)
- [Change Employees](/space/API/93881101)
- [Change Orders](/space/API/93881088)
- [Create Clients](/space/API/93881089)
- [Create Employees](/space/API/93881097)
- [Create Hours](/space/API/93881070)
- [Create memos](/space/API/93881087)
- [Create Orders](/space/API/93881082)
- [Create Traces](/space/API/93881083)
- [Increase Id's](/space/API/93881086)
- [Keep Alive](/space/API/93881103)
- [Request​ Distances](/space/API/93881076)
- [Request Client by Id](/space/API/93881077)
- [Request Employees](/space/API/93881095)
- [Request Hours](/space/API/93881085)
- [Request Invoices](/space/API/93881091)
- [Request Job by Id](/space/API/93881072)
- [Request Job Id's](/space/API/93881081)
- [Request Job Progress](/space/API/93881093)
- [Request Order by Id](/space/API/93881100)
- [Request Order Id's](/space/API/93881074)
- [Request Packaging Transactions](/space/API/93881075)
- [Request Questionnaire by TaskId](/space/API/93881090)
- [Request Questionnaire Question-Answer Pairs](/space/API/479461535)
- [Request Rides (compact)](/space/API/93881092)
- [Request Traces](/space/API/93881069)
- [Requesting Date+Time](/space/API/93881096)
- [Request Last Positions of Rides](/space/API/511705089)
- [Store Job Completed](/space/API/93881080)
- [Store Job Progress](/space/API/93881078)
- [Store Measurement](/space/API/93881098)
- [Store Orderimport Status](/space/API/93881079)
- [Store Ride](/space/API/93881073)
- [Store Ride Timewindow](/space/API/93881094)

---

## Request Traces - Informatie voor ontwikkelaars - MendriX Support & Documentatie

_Bron: https://support.mendrix.nl/space/API/93881069/Request+Traces_

# Request Traces

It is possible to request traces from Custom Link which match specified criteria. The following files contain examples of a request and a response.

- Connect module Custom Link.
  - Send a EoCustomLinkRequestTracesGoods XML request.
  - Receive the EoCustomLinkResponseTracesGoods XML response.
- Disconnect module Custom Link

> For other (important) information, always read Getting Started first.

## Timebased filter

The default period filters in Custom Link are based on dates, so the date element in the period is ignored. For traces there is support for a specific (time sensitive) filter type `TEoTimeAwareFilterTracesGoods` which can be used in a command as follows.

```xml
<?xml version="1.0" encoding="windows-1252"?>
<EoCustomLinkRequestTracesGoods Type="TEoCustomLinkRequestTracesGoods" xsi:noNamespaceSchemaLocation="GdxEoStructures.xsd" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <Filter Type="TEoTimeAwareFilterTracesGoods">
	<PeriodBegin>2025-04-11T00:00:00</PeriodBegin>
	<PeriodEndExclusive>2025-04-11T01:00:00</PeriodEndExclusive>
  </Filter>
</EoCustomLinkRequestTracesGoods>
```

## Example Files

```
\Bin\Metadata\EoCustomLinkRequestTracesGoods.xml
\Bin\Metadata\EoCustomLinkResponseTracesGoods.xml
```

---

## Create Hours - Informatie voor ontwikkelaars - MendriX Support & Documentatie

_Bron: https://support.mendrix.nl/space/API/93881070/Create+Hours_

# Create Hours

## Steps

It is possible to create hours shifts for operators via Custom Link. These steps are needed:

- Connect module Custom Link.
- Send a EoCustomLinkStoreHours XML request.
- Receive the EoStoreResultList XML response.
- Disconnect module Custom Link

## Example

### Request

```xml
<?xml version="1.0" encoding="windows-1252"?>
<EoCustomLinkStoreHours Type="TEoCustomLinkStoreHours" xsi:noNamespaceSchemaLocation="GdxEoStructures.xsd" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
    <Data Type="TEoHoursShiftList">
        <_TEoListBase_Items>
            <EoHoursShift Type="TEoHoursShift">
                <Id>-1</Id>
                <TimeWindow Type="TEoDateTimeWindow">
                    <DateTimeEnd>2008-11-04T08:00:00</DateTimeEnd>
                    <DateTimeBegin>2008-11-04T13:00:00</DateTimeBegin>
                </TimeWindow>
                <OperatorId>104</OperatorId>
                <VehicleId>0</VehicleId>
                <DateTimeExported>1899-12-30T00:00:00</DateTimeExported>
                <TimeChanged>2008-11-04T15:14:10</TimeChanged>
                <TimeVerified>1899-12-30T00:00:00</TimeVerified>
                <Sequence>0</Sequence>
                <AutomaticCreated>False</AutomaticCreated>
                <IsMultipleDayDrive>False</IsMultipleDayDrive>
                <TimeExtraPause>1899-12-30T00:30:00</TimeExtraPause>
                <MileageBegin>0</MileageBegin>
                <MileageEnd>0</MileageEnd>
                <Closed>False</Closed>
                <_TEoListBase_Items>
                    <EoHoursPath Type="TEoHoursPath">
                        <Id>-2</Id>
                        <Index>0</Index>
                        <PathListId>-1</PathListId>
                        <ActivityId>2</ActivityId>
                        <MileageBegin>0</MileageBegin>
                        <MileageEnd>0</MileageEnd>
                        <TimeWindow Type="TEoDateTimeWindow">
                            <DateTimeEnd>2008-11-04T08:00:00</DateTimeEnd>
                            <DateTimeBegin>2008-11-04T12:00:00</DateTimeBegin>
                        </TimeWindow>
                        <VehicleId>2</VehicleId>
                        <StatusBoardComputer>0</StatusBoardComputer>
                        <StatusBoardComputerMomentToUpdate>1899-12-30T00:00:00</StatusBoardComputerMomentToUpdate>
                    </EoHoursPath>
                    <EoHoursPath Type="TEoHoursPath">
                        <Id>-3</Id>
                        <Index>0</Index>
                        <PathListId>-1</PathListId>
                        <ActivityId>2</ActivityId>
                        <MileageBegin>0</MileageBegin>
                        <MileageEnd>0</MileageEnd>
                        <TimeWindow Type="TEoDateTimeWindow">
                            <DateTimeEnd>2008-11-04T12:00:00</DateTimeEnd>
                            <DateTimeBegin>2008-11-04T13:00:00</DateTimeBegin>
                        </TimeWindow>
                        <VehicleId>2</VehicleId>
                        <StatusBoardComputer>0</StatusBoardComputer>
                        <StatusBoardComputerMomentToUpdate>1899-12-30T00:00:00</StatusBoardComputerMomentToUpdate>
                    </EoHoursPath>
                </_TEoListBase_Items>
            </EoHoursShift>
        </_TEoListBase_Items>
    </Data>
</EoCustomLinkStoreHours>
```

### Response

```xml
<?xml version="1.0" encoding="windows-1252"?>
<EoStoreResultList Type="TEoStoreResultList">
    <_TEoListBase_Items>
        <EoStoreResult Type="TEoStoreResult">
            <Id>736</Id>
            <IdOld>-1</IdOld>
            <RowsAffected>1</RowsAffected>
            <StoreDescription></StoreDescription>
            <StoreDetail>0</StoreDetail>
            <StoreResult>srInserted</StoreResult>
        </EoStoreResult>
    </_TEoListBase_Items>
</EoStoreResultList>
```

## In MendriX

A shift with the following data has been created:

![dienst.png](/download/attachments/93881070/dienst.png?version=1&modificationDate=1605891575694&cacheVersion=1&api=v2)

---

## Request Job by Id - Informatie voor ontwikkelaars - MendriX Support & Documentatie

_Bron: https://support.mendrix.nl/space/API/93881072/Request+Job+by+Id_

# Request Job by Id

## Request

```xml
<?xml version="1.0" encoding="windows-1252"?>
<EoCustomLinkRequestJobs Type="TEoCustomLinkRequestJobs" 
 xsi:noNamespaceSchemaLocation="GdxEoStructures.xsd"  xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
    <Nested>False</Nested>
    <Filter Type="TEoFilterJobs">
        <KeysExplicitAsCsv>20</KeysExplicitAsCsv>
    </Filter>
</EoCustomLinkRequestJobs>
```

## Response

```xml
<?xml version="1.0" encoding="windows-1252"?>
<EoCustomLinkResponseJobs Type="TEoCustomLinkResponseJobs">
    <Data Type="TEoJobList">
        <_TEoListBase_Items>
            <EoJobOrderImport Type="TEoJobOrderImport">
                <Id>6</Id>
                <JobTypeId>1</JobTypeId>
                <StatusId>1</StatusId>
                <MomentStarted>2015-09-23T15:16:42+02:00</MomentStarted>
                <MomentCompleted>1899-12-30T00:00:00+01:00</MomentCompleted>
                <TemplateDefinition>{"IncludesHeader":true}</TemplateDefinition>
                <FileUploadId>8</FileUploadId>
                <ClientId>110</ClientId>
                <ContactId>0</ContactId>
                <ProductId>0</ProductId>
                <Filename>Orders Import Example.xls</Filename>
            </EoJobOrderImport>
        </_TEoListBase_Items>
    </Data>
</EoCustomLinkResponseJobs>
```

StatusId    STATUS_UNDEFINED = 0;     STATUS_PENDING = 1;     STATUS_WORKING = 2;     STATUS_COMPLETED = 3;     STATUS_CANCELLED = 4;     STATUS_WARNING = 5;     STATUS_ERROR = 6;

JobTypeId:     TYPE_UNDEFINED = 0;     TYPE_ORDERIMPORT = 1;

---

## Store Ride - Informatie voor ontwikkelaars - MendriX Support & Documentatie

_Bron: https://support.mendrix.nl/space/API/93881073/Store+Ride_

# Store Ride

## Request

```xml
<?xml version="1.0" encoding="windows-1252"?>
<EoCustomLinkStoreRides Type="TEoCustomLinkStoreRides" xsi:noNamespaceSchemaLocation="GdxEoStructures.xsd" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <JobInfoOrderImport Type="TEoCustomLinkJobInfoOrderImport">
    <JobId>20</JobId>
    <RowIds Type="TEoKeyIntList">
      <SequenceMaximum>0</SequenceMaximum>
      <_TEoListBase_Items>
        <EoKeyInt Type="TEoKeyInt">
          <Id>1</Id>
        </EoKeyInt>
      </_TEoListBase_Items>
    </RowIds>
  </JobInfoOrderImport>
  <Data Type="TEoCustomLinkRideList">
    <_TEoListBase_Items>
      <EoCustomLinkRide Type="TEoCustomLinkRide">
        <Id>-1</Id>
        <JobId>0</JobId>
        <NameManual>Rit 230</NameManual>
        <MomentStart>2015-07-22T10:00:00</MomentStart>
        <MomentEnd>2015-07-22T22:00:00</MomentEnd>
      </EoCustomLinkRide>
    </_TEoListBase_Items>
  </Data>
</EoCustomLinkStoreRides>
```

- JobId: leave out or set to 0, except when importing for a specific job.

## Response

```xml
<?xml version="1.0" encoding="windows-1252"?>
<EoStoreResultList Type="TEoStoreResultList">
<_TEoListBase_Items>
<EoStoreResult Type="TEoStoreResult">
 <Id>30</Id>
 <IdOld>0</IdOld>
 <RowsAffected>1</RowsAffected>
 <StoreDescription></StoreDescription>
 <StoreDetail>0</StoreDetail>
 <StoreResult>srInserted</StoreResult>
</EoStoreResult>
</_TEoListBase_Items>
</EoStoreResultList>
```

---

## Request Order Id's - Informatie voor ontwikkelaars - MendriX Support & Documentatie

_Bron: https://support.mendrix.nl/space/API/93881074/Request+Order+Id's_

# Request Order Id's

Requesting orders is a multi-step process. First use below command 'EoCustomLinkRequestOrdersNormalIds' to request all the Id's of the orders conforming your criteria. See the last step below on a reference how to retrieve the actual data of the orders after you got the Id's.

> For other (important) information, always read [Getting Started](/space/API/93881066) first.​

## Steps

## Step 1 - Connect

Connect module Custom Link.

## Step 2 - Request Id's

​Send the request to retrieve the Id's of orders meeting your criteria. The next example retrieves the Id's of the orders of client Id 110 of januari 2012. If you change the ClientNo to -1 it will not filter on client. It works the same for OperatorId. If specifying -1 then there is no limiting filter on the operator that performs the tasks of the order. It is possible to request Id's for more than one operator. Seperate all operatorid's with comma's, like 130,131,152.

> Note: ClientNo is the database key of the client, not the editable 'Number' of the client.

> note: OperatorId can be used to filter more than one operator. More Id's can be provided as CSV. Like '130, 38,150'. This functionality is available from MendriX version 2013.4.0.0

```xml
<?xml version="1.0" encoding="windows-1252"?>
<EoCustomLinkRequestOrdersNormalIds Type="TEoCustomLinkRequestOrdersNormalIds" xsi:noNamespaceSchemaLocation="GdxEoStructures.xsd" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <Nested>False</Nested>
  <Filter Type="TEoFilterOrdersNormal">
    <PeriodBegin>2012-01-01T00:00:00</PeriodBegin>
    <PeriodEnd>2012-01-31T00:00:00</PeriodEnd>
    <ClientNo>110</ClientNo>
    <OperatorId>-1</OperatorId>
  </Filter>
</EoCustomLinkRequestOrdersNormalIds>
```

## Step 3 - Receive Id's

Now receive the resulting Id's from module Custom Link.

```xml
<?xml version="1.0" encoding="windows-1252"?>
<EoCustomLinkResponseOrdersNormalIds Type="TEoCustomLinkResponseOrdersNormalIds">
<Data Type="TEoKeyIntList">
 <SequenceMaximum>7086</SequenceMaximum>
<_TEoListBase_Items>
<EoKeyInt Type="TEoKeyInt">
 <Id>349</Id>
</EoKeyInt>
<EoKeyInt Type="TEoKeyInt">
 <Id>371</Id>
</EoKeyInt>
<EoKeyInt Type="TEoKeyInt">
 <Id>391</Id>
</EoKeyInt>
<EoKeyInt Type="TEoKeyInt">
 <Id>401</Id>
</EoKeyInt>
..
```

## Step 4 - Disconnect

Now disconnect module Custom Link.

## Step 5 - Use received Id's to retrieve the whole order

The second  step is to use the retrieved list of Id's to request the actual data of the orders themselves one by one (or as a batch) [using the command "EoCustomLinkRequestOrdersNormal"](/space/API/93881100).

# Using 'Sequence'

The 'sequence' is a database wide incremental counter which gets incremented by one each time a change is committed to the database. All items changed within this transaction get this new sequence. So imagine you have an order with sequence 123 and you have a client with sequence 123. After committing a change to this client, both this client  and the database get sequence 124, but mind that the order still has sequence 123. Now if you change that order, then both the order and the database get sequence 125, but the client still remains 124 (because it was not changed this time).

When requesting the order Id's of the order, the returned list with Id's contains a field 'SequenceMaximum', which is the maximum sequence of the orders of the Id's returned, for example '123'. Now when you would run the exact same request again, normally you would get the exact same result again. However, now try to run the exact same XML request, but now specify the node 'SequenceMinimum' and give it the value '124' (without quotes, and one higher than the maximum sequence in the earlier result-set). Now you only get the orders conforming to your request which have actually changed. Note that in the request we use SequenceMinimum and not SequenceMaximum, thus instructing Custom Link only to return data with at least the given sequence.

> Tip: Using the sequence to limit your resultset en limit the load on the server is highly recommended, though not required.

> Important: Sequence is not updated immediately within the same transaction as a store. Even when saving data in the MendriX TMS application. The Sequence is updated in a background process to prevent the store from being delayed too much. This background process might take one to several seconds to update the Sequence values in accordance with to the database changes that have been done. So when requesting for data based on Sequence does not ensure you have ALL the newest data. Some delay must be taken into account.

## Using 'IgnShowAlways' with sequences

The node "IgnShowAlways" determines if orders which have been configured to be always visible in MendriX TMS should be included in the resulting list of order id's. By default this node is set to "False", meaning orders which are always visible will be included in the list of order Id's, even if the orders in question do not match the given filter. The only exception is the usage of seqeunces. Including "SequenceMinimum" or "SequenceMaximum" with the request will always return a list of order Id's matching the given sequence range.

> Important: setting "IgnShowAlways" to "True" will cause Custom Link to ignore the sequence range specified in the request! If you require a list of order Id's within a specific sequence range, set "IgnShowAlways" to "False" or leave it out of the request.

# Specifying a period other than the default today

When requesting order id's, the default period is one day (today). If no period is provided in the request, this is the period orders will be first filtered upon. To request order id's within a certain period, you have to add the nodes "PeriodBegin" (inclusive begin date of the period) and "PeriodEnd" (inclusive end date of the period). See the example at the top of this page for more information.

## How an order matches the period

An order is returned when **any of its tasks is active at some point within the requested period** — that is, when the task's requested service window (Requested-To-Arrive … Requested-To-Depart) **overlaps** the period [PeriodBegin … PeriodEnd]. A task is also matched when its Requested-To-Arrive, Requested-To-Depart or Planned-To-Arrive moment falls inside the period, so planned-but-not-yet-driven tasks remain visible.

In particular this includes tasks whose window *straddles* the requested period: a task requested to arrive **before** PeriodBegin and to depart **after** PeriodEnd is active on every day in between, so its order is returned even though neither endpoint falls inside the period.

*Example* — a task requested from 10 March to 25 March is returned by a request for the period 15 March – 20 March, because the task is active across that whole window.

**Behaviour change (MendriX 2026.2):** in earlier versions an order was only returned when a task *moment* fell inside the requested period; tasks whose window straddled the period (active across it, but with neither endpoint inside it) were not returned. From 2026.2 such orders are correctly included. If you maintain an integration that depends on the old point-in-period behaviour, see *Reverting to the legacy period matching* below.

## Reverting to the legacy period matching (compatibility switch)

The overlap matching described above is the default. If an existing integration relies on the previous point-in-period behaviour, you can opt a single request back to it by adding the optional node `UseLegacyOrderFilterPeriodMatching` to the filter:

```xml
<Filter Type="TEoFilterOrdersNormal">
  <PeriodBegin>2012-01-01T00:00:00</PeriodBegin>
  <PeriodEnd>2012-01-31T00:00:00</PeriodEnd>
  <ClientNo>110</ClientNo>
  <OperatorId>-1</OperatorId>
  <UseLegacyOrderFilterPeriodMatching>True</UseLegacyOrderFilterPeriodMatching>
</Filter>
```

When the node is absent or `False` (the default), the new overlap matching applies. This switch is a temporary compatibility aid, intended to be removed in a future version once all integrations have adopted the new behaviour — do not rely on it for new development.

An installation-wide equivalent exists as the `UseLegacyOrderFilterPeriodMatching` feature flag in the server's settings; a MendriX administrator can enable it for an entire installation. Contact MendriX support if you need this.

# Example Files

```
Bin\Metadata\EoCustomLinkRequestOrdersNormalIds.xml
Bin\Metadata\EoCustomLinkResponseOrdersNormalIds.xml
```

---

## Request Packaging Transactions - Informatie voor ontwikkelaars - MendriX Support & Documentatie

_Bron: https://support.mendrix.nl/space/API/93881075/Request+Packaging+Transactions_

# Request Packaging Transactions

## Request

```xml
<?xml version="1.0"?>
<EoCustomLinkRequestPackagingTransactions Type="TEoCustomLinkRequestPackagingTransactions" 
 xsi:noNamespaceSchemaLocation="GdxEoStructures.xsd" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
    <Nested>False</Nested>
    <Filter Type="TEoFilterPackagingTransactions">
        <OrderIdsAsCsv>230</OrderIdsAsCsv>
    </Filter>
</EoCustomLinkRequestPackagingTransactions>
```

## Response

```xml
<?xml version="1.0" encoding="windows-1252"?>
<EoPackagingTransactionList Type="TEoPackagingTransactionList">
<_TEoListBase_Items>
<EoPackagingTransaction Type="TEoPackagingTransaction">
 <Id>11</Id>
 <TaskId>628</TaskId>
 <TaskState>1200</TaskState>
 <TaskType>1</TaskType>
 <TaskTypeEx>1</TaskTypeEx>
 <OrderId>230</OrderId>
 <PackingId>5</PackingId>
 <PackingName>Rolcontainer</PackingName>
 <TransferIn>42</TransferIn>
 <TransferOut>0</TransferOut>
</EoPackagingTransaction>
<EoPackagingTransaction Type="TEoPackagingTransaction">
 <Id>12</Id>
 <TaskId>629</TaskId>
 <TaskState>1200</TaskState>
 <TaskType>2</TaskType>
 <TaskTypeEx>2</TaskTypeEx>
 <OrderId>230</OrderId>
 <PackingId>6</PackingId>
 <PackingName>Pallet</PackingName>
 <TransferIn>0</TransferIn>
 <TransferOut>230</TransferOut>
</EoPackagingTransaction>
</_TEoListBase_Items>
</EoPackagingTransactionList>
```

---

## Request​ Distances - Informatie voor ontwikkelaars - MendriX Support & Documentatie

_Bron: https://support.mendrix.nl/space/API/93881076/Request%E2%80%8B+Distances_

# Request​ Distances

## Steps

Distances and durations can be requested of a list of country and postalcode combinations. This only works properly for The Netherlands and you have to have a valid module Postcodes Plus NL licence.

> For other (important) information, always read [Getting Started](/space/API/93881066) first.

- Connect module Custom Link.
- First send a proper formatted EoNavigationDistanceAndTimeRequest XML request.
- Then receive a EoNavigationDistanceAndTime XML response.
- Disconnect module Custom Link.

## Example Files

```
Bin\Metadata\EoNavigationDistanceAndTimeRequest.xml
Bin\Metadata\EoNavigationDistanceAndTime.xml
```

---

## Request Client by Id - Informatie voor ontwikkelaars - MendriX Support & Documentatie

_Bron: https://support.mendrix.nl/space/API/93881077/Request+Client+by+Id_

# Request Client by Id

## Steps

It is possible to request clients from Custom Link which match specified criteria. The following files contain examples of a request and a response.

- Connect module Custom Link.
- Send a EoCustomLinkRequestClients XML request.
- Receive the EoCustomLinkResponseClients XML response.
- Disconnect module Custom Link

> For other (important) information, always read [Getting Started](/space/API/93881066) first.

## Example Files

```
\Bin\Metadata\EoCustomLinkRequestClients.xml
\Bin\Metadata\EoCustomLinkResponseClients.xml
```

---

## Store Job Progress - Informatie voor ontwikkelaars - MendriX Support & Documentatie

_Bron: https://support.mendrix.nl/space/API/93881078/Store+Job+Progress_

# Store Job Progress

## Request

```xml
<?xml version="1.0" encoding="windows-1252"?>
<EoCustomLinkStoreJobProgress Type="TEoCustomLinkStoreJobProgress">
    <Data Type="TEoCustomLinkJobProgress">
        <StatusId>3</StatusId>
        <JobId>6</JobId>
        <Progress Type="TEoJobProgressOrderImport">
            <RowCount>15</RowCount>
            <RowCurrent>12</RowCurrent>
            <RetryCount>1</RetryCount>
        </Progress>
    </Data>
</EoCustomLinkStoreJobProgress>
```

STATUS_UNDEFINED = 0; STATUS_PENDING = 1; STATUS_WORKING = 2; STATUS_COMPLETED = 3; STATUS_CANCELLED = 4; STATUS_WARNING = 5; STATUS_ERROR = 6;

## Response

```xml
<?xml version="1.0" encoding="windows-1252"?>
<EoStoreResultList Type="TEoStoreResultList">
<_TEoListBase_Items>
<EoStoreResult Type="TEoStoreResult">
 <Id>6</Id>
 <IdOld>6</IdOld>
 <RowsAffected>0</RowsAffected>
 <StoreDescription></StoreDescription>
 <StoreDetail>0</StoreDetail>
 <StoreResult>srUpdated</StoreResult>
 <ErrorType>etNone</ErrorType>
</EoStoreResult>
</_TEoListBase_Items>
</EoStoreResultList>
```

---

## Store Orderimport Status - Informatie voor ontwikkelaars - MendriX Support & Documentatie

_Bron: https://support.mendrix.nl/space/API/93881079/Store+Orderimport+Status_

# Store Orderimport Status

## Request

```xml
<?xml version="1.0" encoding="windows-1252"?>
<EoCustomLinkStoreJobOrderImportOrderStatuses Type="TEoCustomLinkStoreJobOrderImportOrderStatuses" xsi:noNamespaceSchemaLocation="GdxEoStructures.xsd" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
    <Data Type="TEoJobOrderImportOrderStatusList">
        <_TEoListBase_Items>
            <EoJobOrderImportOrderStatus Type="TEoJobOrderImportOrderStatus">
                <Id>-1</Id>
                <JobId>20</JobId>
                <StatusId>1</StatusId>
                <StatusDescription>Broken rabbit eggs</StatusDescription>
                <OrderId>0</OrderId>
                <RowId>10</RowId>
            </EoJobOrderImportOrderStatus>
        </_TEoListBase_Items>
    </Data>
</EoCustomLinkStoreJobOrderImportOrderStatuses>
```

## Response

```xml
<?xml version="1.0" encoding="windows-1252"?>
<EoStoreResultList Type="TEoStoreResultList">
<_TEoListBase_Items>
<EoStoreResult Type="TEoStoreResult">
 <Id>2</Id>
 <IdOld>2</IdOld>
 <RowsAffected>1</RowsAffected>
 <StoreDescription></StoreDescription>
 <StoreDetail>0</StoreDetail>
 <StoreResult>srUpdated</StoreResult>
</EoStoreResult>
</_TEoListBase_Items>
</EoStoreResultList>
```

---

## Store Job Completed - Informatie voor ontwikkelaars - MendriX Support & Documentatie

_Bron: https://support.mendrix.nl/space/API/93881080/Store+Job+Completed_

# Store Job Completed

## Request

```xml
<?xml version="1.0" encoding="windows-1252"?>
<EoCustomLinkStoreJobCompleted Type="TEoCustomLinkStoreJobCompleted">
    <Data Type="TEoCustomLinkJobCompletion">
        <JobId>6</JobId>
        <Moment>2015-09-23T15:16:42+02:00</Moment>
        <StatusId>3</StatusId>
    </Data>
</EoCustomLinkStoreJobCompleted>
```

## Response

```xml
<?xml version="1.0" encoding="windows-1252"?>
<EoStoreResultList Type="TEoStoreResultList">
<_TEoListBase_Items>
<EoStoreResult Type="TEoStoreResult">
 <Id>6</Id>
 <IdOld>6</IdOld>
 <RowsAffected>0</RowsAffected>
 <StoreDescription></StoreDescription>
 <StoreDetail>0</StoreDetail>
 <StoreResult>srUpdated</StoreResult>
 <ErrorType>etNone</ErrorType>
</EoStoreResult>
</_TEoListBase_Items>
</EoStoreResultList>
```

---

## Request Job Id's - Informatie voor ontwikkelaars - MendriX Support & Documentatie

_Bron: https://support.mendrix.nl/space/API/93881081/Request+Job+Id's_

# Request Job Id's

## Request

```xml
<?xml version="1.0" encoding="windows-1252"?>
<EoCustomLinkRequestJobIds Type="TEoCustomLinkRequestJobIds" xsi:noNamespaceSchemaLocation="GdxEoStructures.xsd" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <Nested>False</Nested>
  <Filter Type="TEoFilterJobs">
    <JobTypeId>1</JobTypeId>
  </Filter>
</EoCustomLinkRequestJob>
```

JobTypeId:     TYPE_UNDEFINED = 0;     TYPE_ORDERIMPORT = 1;

## Response

```xml
<?xml version="1.0" encoding="windows-1252"?>
<EoCustomLinkResponseJobIds Type="TEoCustomLinkResponseJobIds">
   <Data Type="TEoKeyIntList">
    <SequenceMaximum>0</SequenceMaximum>
    <_TEoListBase_Items>
       <EoKeyInt Type="TEoKeyInt">
          <Id>20</Id>
       </EoKeyInt>
       <EoKeyInt Type="TEoKeyInt">
          <Id>21</Id>
       </EoKeyInt>
    </_TEoListBase_Items>
   </Data>
</EoCustomLinkResponseJobIds>
```

---

## Create Orders - Informatie voor ontwikkelaars - MendriX Support & Documentatie

_Bron: https://support.mendrix.nl/space/API/93881082/Create+Orders_

# Create Orders

## How to create a (simple) new order

Creating new orders in the storage, is done with the same command as "[Changing Orders](/space/API/93881088)", but with negative identifiers.

> For other (important) information, always read "[Getting Started](/space/API/93881066)" first. Also take a look at "[XML structure and new order](https://wiki.mendrix.nl/space/API/689831937/MendriX+XML+structure%3A+Create+a+new+order)" to understand the basic structure of the order XML.

## Step 1 - Send Store Request

The next XML requests Custom Link to create one single new order, with two tasks (a task is an address) with one good (e.g. package) linked to both tasks. Note the negative Id's of the tasks and the good, signaling the system to create new records. Also note the GoodsToTasks node, which links the good to the tasks. 

> Note: To create new items, identifiers of those items must have a negative value. References in new items to existing data must ofcourse still have a positive valid value.

> There are more fields available then shown in this example. See "[Changing Orders](/space/API/93881088)" for more details and example files, because it uses the same XML lay-out.

```xml
<?xml version="1.0" encoding="windows-1252"?>
							<TaskTypeId Type="TEoKeyIntInfraMx">
								<Id>1</Id>
							</TaskTypeId>
						</EoTaskMx>
						<EoTaskMx Type="TEoTaskMx">
							<TaskId Type="TEoKeyIntInfraMx">
								<Id>-200</Id>
							</TaskId>
							<Address Type="TEoAddress">
								<Name>Vreen & Droosman</Name>
								<Premise/>
								<Street>Rueckertbaan 100</Street>
								<Number/>
								<PostalCode>5042 AG</PostalCode>
								<Place>Tilburg</Place>
								<State/>
								<Country>Nederland</Country>
								<CountryCode>NL</CountryCode>
							</Address>
							<CashOnDelivery>0.0</CashOnDelivery>
							<Connectivity Type="TEoConnectivity">
								<Email/>
								<Fax/>
								<Mobile/>
								<Phone>013-5563822</Phone>
								<Web/>
							</Connectivity>
							<ContactName>Gert van de Lotering</ContactName>
							<Instructions>Neem lege enveloppen mee</Instructions>
							<OperatorIdAutomatic>True</OperatorIdAutomatic>
							<Planned Type="TEoDateTimeWindow">
								<DateTimeEnd>2008-04-02T14:00:00</DateTimeEnd>
								<DateTimeBegin>2008-04-02T14:00:00</DateTimeBegin>
							</Planned>
							<ReferenceOur/>
							<ReferenceYour/>
							<Requested Type="TEoDateTimeWindow">
								<DateTimeEnd>2008-04-02T14:00:00</DateTimeEnd>
								<DateTimeBegin>2008-04-02T14:00:00</DateTimeBegin>
							</Requested>
							<TaskTypeId Type="TEoKeyIntInfraMx">
								<Id>2</Id>
							</TaskTypeId>
						</EoTaskMx>
					</_TEoListBase_Items>
				</Tasks>
				<GoodsToTasks Type="TEoGoodToTaskMxList">
					<_TEoListBase_Items>
						<EoGoodToTaskMx Type="TEoGoodToTaskMx">
							<GoodId Type="TEoKeyIntInfraMx">
								<Id>-1</Id>
							</GoodId>
							<TaskId Type="TEoKeyIntInfraMx">
								<Id>-100</Id>
							</TaskId>
						</EoGoodToTaskMx>
						<EoGoodToTaskMx Type="TEoGoodToTaskMx">
							<GoodId Type="TEoKeyIntInfraMx">
								<Id>-1</Id>
							</GoodId>
							<TaskId Type="TEoKeyIntInfraMx">
								<Id>-200</Id>
							</TaskId>
						</EoGoodToTaskMx>
					</_TEoListBase_Items>
				</GoodsToTasks>
				<ExternalDone>True</ExternalDone>
				<ExternalSource>7</ExternalSource>
			</EoOrderMx>
		</_TEoListBase_Items>
	</Data>
</EoCustomLinkStoreOrdersNormal>
```

## Step 2 - Receive Store Result

After the order is created succesfully, you receive an XML response, which contains the Id(s) of the created order(s). 

```xml
<?xml version="1.0" encoding="windows-1252"?>
<EoStoreResultList Type="TEoStoreResultList">
<_TEoListBase_Items>
<EoStoreResult Type="TEoStoreResult">
 <Id>406</Id>
 <IdOld>-1</IdOld>
 <RowsAffected>1</RowsAffected>
 <StoreDescription></StoreDescription>
 <StoreDetail>0</StoreDetail>
 <StoreResult>srInserted</StoreResult>
</EoStoreResult>
</_TEoListBase_Items>
</EoStoreResultList>
```

> Tip: The response contains pairs of your originally specified negative Id's en the new positive Id's those items got in the database.

## Specific Address fields: Street, house number and addition

Concering the specific fields, the street, house number and addition. It is better to send street and house number separately. Additions must be in the number field. It is better that there no spaces or other white spaces are used. For compatibility reasons some parts of MendriX or links, street and number are used as one field. The house number will be cut again on the basis of the numbers plus all the characters that stand behind it. If there are spaces between the house and addition, MendriX can no longer distinguish what belongs to the house number and what belongs to the street.

## Good characteristics

It is possible to store good characteristics for each good. These are optional fields. To add good chracteristics add the following elements inside the `<EoGoodMx Type="TEoGoodMx">` element for each good:

```xml
<Characteristics Type="TGoodCharacteristicsRestricted">                        
	<IdsAsCsv>2,3</IdsAsCsv>
</Characteristics>
```

The good characteristics are stored via id's in a comma seperated string inside the `<IdsAsCsv>` element. The following good characteristics are possible:

- **2**: NoNextDoor;
  - Good is not allowed to be delivered to any neighboring address; 

- **3**: Confidential;
  - Good is marked as a confidential package;

- **4**: ADR;
  - Good is marked as an ADR dangerous good;

- **18**: Age 18+
  - Good is marked as an 18 plus good. The recipient of the good should be age 18 or older;

- **40**: Cool;
  - Good should be kept at a cool temperature (range between 2 and 8 degrees C);

- **41**: Freeze;
  - Good should be kept at a Freezing temperature (range between -18 and -10 degrees C);

- **42**: DryAmbient;
  - Good should be kept dry and at an ambient temperature (range between 16 and 22 degrees C);

- **43**: DeepFreeze;
  - Good should be kept at a Deep Freeze temperature (range between -273 and -18 degrees C);

### Restraints and behavior for good characteristics

When a good receives certain good characteristics the order stored could have behavioral side effects or certain good characteristics have restraints:

- If a good receives an **ADR (id: 4)** good characteristic the order stored will be marked as "ADR mandatory for vehicle and operator".

- If a good receives either a **Cool (id: 40), Freeze (id: 41), DryAmbient (id: 42)** or **DeepFreeze (id: 43)**:
  - good characteristic the order stored will be marked as "Refrigeration installation mandatory for vehicle and operator".
  - The temperature of the good will also be set to the correct corrosponding temperature range.
  - Only one of these good characteristics can be set for each good. If more temperature based good characteristics are set for a good only the last received temperature good characteristic will be set. Example, if `<IdsAsCsv>40,41,42,43</IdsAsCsv>` was received only 43 will be set on that good.

## Products and articles

Note that articles will not be modified, neither manualy nor by automatic values, when the order is on an invoice.

### Automatic articles (field EoOrder.ProductIdAutomaticArticles)

If this field is True, all the +automatic+articles of the given ProductId will be added and calculated using the specific prices for the given relation. Use this options if you don't specify any article using the ArticleSell-tags.

### Specify article but let MendriX determine the Number (field EoArticle.NumberManual)

If this field is True, MendriX will recalculate the Number using the automatisch article type of the specified ArticleIdForeign.

### Specifiy number but let MendriX determine the Price (field EoArticle.PriceManual)

If this field is True, MendriX will recalculate the pricing fields using the Number-field (see previous section). Of course the graduates or other relationspecific prices will be respected.

## Applying settings

It's possible to let Custom Link apply settings as configured in MendriX. To do this, use the field EoCustomLinkStoreOrdersNormal.ApplyImportSettings. This has the following effects:

- OrderId is copied to OrderReference if OrderReference isn't speficied in the request, and setting WorldLink.CopyOrderIdToReference=True.

- TimeWindows are tasks are update based on the settings of the product.

- The order is automatically confirmed (preplanned-flag is unset), if setting Orders.DefaultConfirmOrdSub=1.

- Automatic invoice description of the order is enabled or disabled based on setting Orders.DefaultAutoInvoiceDescriptionEnabled.

- The OrderType is changed to Concept if setting WorldLink.OrderImportNewOrdersConcept=True.

- The InvoiceStatus is changed to "Ready to be invoiced" if setting Orders.DefaultGoodForInvoice=True.

- If no categories are specified in the request, the categories are changed to the categories as specified in the relation.

- The way the distance/duraction is calculated is changed based on setting Distances.KmsCalcTaskCircle.

- If no start and end address are specified in the request, these are entered based on start and end address from the relation or the administration of the relation.

- If no country is specified for the tasks, the default country is entered, based on setting General.DefaultCountry.

- Goods are split in separate lines, when goods with multiple parts are specified in the request (based on setting WorldLink.GoodsRowsOrPartsCount).

- If the order has tasks but no goods, one good is added automatically.

## Creating different types of orders

- In order to create a concept order add; `<OrderType>100</OrderType>`

- In order to create a offerte order add; `<OrderType>200</OrderType>`

## How to create a (complex) order with sold articles in it

Below example creates one order in MendriX TMS with two adresses in it (one pick-up and one deliver address), with two goods in it connected to both tasks and also two articles in it of Id 44 with each it's own prices. The result of below XML is one order with a total price of €55.55, because two articles are added with a fixed price of one €22.22 and the second of €33.33.

### Step 1 - Send Store Request

```xml
<?xml version="1.0" encoding="windows-1252"?>
              <AmountArticle>0.0</AmountArticle>
              <ArticleId Type="TEoKeyIntInfraMx">
                <Id>-10</Id>
              </ArticleId>
              <ArticleIdForeign Type="TEoKeyIntInfraMx">
                <Id>44</Id>
              </ArticleIdForeign>
              <Automatic>False</Automatic>
              <CalculatedWithGraduates>False</CalculatedWithGraduates>
              <Extra>22.22</Extra>
              <Minimum></Minimum>
              <Number>1</Number>
              <NumberFree>0</NumberFree>
              <NumberRaw>1</NumberRaw>
              <Percentage>0</Percentage>
              <PercentageTypeId>0</PercentageTypeId>
              <Price>0</Price>
              <PriceManual>True</PriceManual>
              <NumberManual>True</NumberManual>
              <SortOrder>1</SortOrder>
            </EoArticleSell>
          <ArticlesSell Type="TEoArticleList">
          <_TEoListBase_Items>
            <EoArticleSell Type="TEoArticleSell">
              <AmountArticle>0.0</AmountArticle>
              <ArticleId Type="TEoKeyIntInfraMx">
                <Id>-20</Id>
              </ArticleId>
              <ArticleIdForeign Type="TEoKeyIntInfraMx">
                <Id>44</Id>
              </ArticleIdForeign>
              <Automatic>False</Automatic>
              <CalculatedWithGraduates>False</CalculatedWithGraduates>
              <Extra>33.33</Extra>
              <Minimum></Minimum>
              <Number>1</Number>
              <NumberFree>0</NumberFree>
              <NumberRaw>1</NumberRaw>
              <Percentage>0</Percentage>
              <PercentageTypeId>0</PercentageTypeId>
              <Price>0</Price>
              <PriceManual>True</PriceManual>
              <NumberManual>True</NumberManual>
              <SortOrder>1</SortOrder>
            </EoArticleSell>
          </_TEoListBase_Items>
        </ArticlesSell>
       <ExternalDone>False</ExternalDone>
        <ExternalSource>195</ExternalSource>
      </EoOrderMx>
    </_TEoListBase_Items>
  </Data>
</EoCustomLinkStoreOrdersNormal>
```

### Step 2 - Receive Store Result

After the order is created succesfully, you receive an XML response, which contains the Id(s) of the created order(s). 

```xml
<?xml version="1.0" encoding="windows-1252"?>
<EoStoreResultList Type="TEoStoreResultList">
<_TEoListBase_Items>
<EoStoreResult Type="TEoStoreResult">
 <Id>406</Id>
 <IdOld>-1000</IdOld>
 <RowsAffected>1</RowsAffected>
 <StoreDescription></StoreDescription>
 <StoreDetail>0</StoreDetail>
 <StoreResult>srInserted</StoreResult>
</EoStoreResult>
</_TEoListBase_Items>
</EoStoreResultList>
```

> Tip: The response contains pairs of your originally specified negative Id's en the new positive Id's those items got in the database.​

---

## Create Traces - Informatie voor ontwikkelaars - MendriX Support & Documentatie

_Bron: https://support.mendrix.nl/space/API/93881083/Create+Traces_

# Create Traces

## Steps

It is possible to create traces for goods via Custom Link. These steps are needed:

- Connect module Custom Link.
- Send a EoCustomLinkStoreTracesGoods XML request.
- Receive the EoStoreResultList XML response.
- Disconnect module Custom Link

## Example

### Request:

```xml
<?xml version="1.0" encoding="windows-1252"?>
<EoCustomLinkStoreTracesGoods Type="TEoCustomLinkStoreTracesGoods" 
  xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="GdxEoStructures.xsd">
    <Data Type="TEoTraceList">
        <_TEoListBase_Items>
            <EoTraceGoods Type="TEoTraceGoods">
                <Id>-1</Id>
                <GoodId>429</GoodId>
                <Moment>2009-11-12T15:19:04+01:00</Moment>
                <TraceTypeId>3</TraceTypeId>
            </EoTraceGoods>
            <EoTraceGoods Type="TEoTraceGoods">
                <Id>-2</Id>
                <GoodId>429</GoodId>
                <Moment>2009-11-12T15:18:59+01:00</Moment>
                <TraceTypeId>2</TraceTypeId>
            </EoTraceGoods>
        </_TEoListBase_Items>
    </Data>
</EoCustomLinkStoreTracesGoods>
```

### Response

```xml
<?xml version="1.0" encoding="windows-1252"?>
<EoStoreResultList Type="TEoStoreResultList">
    <_TEoListBase_Items>
        <EoStoreResult Type="TEoStoreResult">
            <Id>601</Id>
            <IdOld>-1</IdOld>
            <RowsAffected>1</RowsAffected>
            <StoreDescription></StoreDescription>
            <StoreDetail>0</StoreDetail>
            <StoreResult>srInserted</StoreResult>
        </EoStoreResult>
        <EoStoreResult Type="TEoStoreResult">
            <Id>602</Id>
            <IdOld>-2</IdOld>
            <RowsAffected>1</RowsAffected>
            <StoreDescription></StoreDescription>
            <StoreDetail>0</StoreDetail>
            <StoreResult>srInserted</StoreResult>
        </EoStoreResult>
    </_TEoListBase_Items>
</EoStoreResultList>
```

## In MendriX

This results in two new traces in MendriX for good 429. One of the traces has tracetype 3 ("Opgehaald" in this database), the other 2 ("Aangemeld".

This also works for orders which are already on an invoice.

## Example File

```
\Bin\Metadata\EoCustomLinkStoreTracesGoods .xml
```

---

## Request Hours - Informatie voor ontwikkelaars - MendriX Support & Documentatie

_Bron: https://support.mendrix.nl/space/API/93881085/Request+Hours_

# Request Hours

## Steps

It is possible to request hours shifts from Custom Link which match specified criteria. The following files contain examples of a request and a response.

- Connect module Custom Link.
- Send a EoCustomLinkRequestHours XML request.
- Receive the EoCustomLinkResponseHours XML response.
- Disconnect module Custom Link

> For other (important) information, always read [Getting Started](/space/API/93881066) first.

## Example Files

```
\Bin\Metadata\EoCustomLinkRequestHours.xml
\Bin\Metadata\EoCustomLinkResponseHours.xml
```

---

## Increase Id's - Informatie voor ontwikkelaars - MendriX Support & Documentatie

_Bron: https://support.mendrix.nl/space/API/93881086/Increase+Id's_

# Increase Id's

## Introduction

Id's can be increased with a custom value.

## Sending an increase request

The following XML requests the OrderId to be increased with 189:

```xml
<?xml version="1.0" encoding="windows-1252"?>
<EoCustomLinkStoreIncreaseNextId Type="TEoCustomLinkStoreIncreaseNextId">
  <Data Type="TEoBase"/>
  <Name>OrderId</Name>
  <Amount>189</Amount>
</EoCustomLinkStoreIncreaseNextId>
```

The **Name** node determines the type of Id to be increased, while the **Amount** node holds the amount with which the Id will be increased.

### Limitations

Currently the **Name** node only accepts the value "OrderId". The amount specified in the **Amount** node has a minimum of 0 (zero) and a maximum of 200.

## Receiving results

Once the increase request has been processed, the following response is sent back:

```xml
<EoStoreResult Type="TEoStoreResult">
  <Id>0</Id>
  <IdOld>0</IdOld>
  <RowsAffected>0</RowsAffected>
  <StoreDescription></StoreDescription>
  <StoreDetail>0</StoreDetail>
  <StoreResult>srUpdated</StoreResult>
</EoStoreResult>
```

After a successful increase the node **StoreResult** will have the value *srUpdated* or *srInserted*. If an error occurred during the increase, the node **StoreResult** will have the value *srError*. The error description will be sent with the **StoreDescription** node.

Please note: the value of the updated Id is not sent with the result XML.

---

## Create memos - Informatie voor ontwikkelaars - MendriX Support & Documentatie

_Bron: https://support.mendrix.nl/space/API/93881087/Create+memos_

# Create memos

## Sending request

The following XML requests a single memo to be created:

```xml
<?xml version="1.0" encoding="windows-1252"?>
<EoCustomLinkStoreMemos Type="TEoCustomLinkStoreMemos" xsi:noNamespaceSchemaLocation="GdxEoStructures.xsd" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
<Data Type="TEoMemoList">
<_TEoListBase_Items>
<EoMemo Type="TEoMemo">
 <Alarm>2011-07-25T09:07:45</Alarm>
 <Audible>True</Audible>
 <AutoDelete>True</AutoDelete>
 <MasterId>346</MasterId>
 <MemoType>mtManual</MemoType>
 <Moment>2011-07-25T09:07:45</Moment>
 <Priority>0</Priority>
 <SectionIndex>seiOrdsNm</SectionIndex>
 <Subject>Nieuwe Custom Link order</Subject>
 <Text>Er is een nieuwe order ingevoerd via Custom Link</Text>
 <Visible>True</Visible>
</EoMemo>
</_TEoListBase_Items>
</Data>
</EoCustomLinkStoreMemos>
```

## Receiving results

After the request has been processed, the following response is sent back:

```xml
<?xml version="1.0" encoding="windows-1252"?>
<EoStoreResultList Type="TEoStoreResultList">
<_TEoListBase_Items>
<EoStoreResult Type="TEoStoreResult">
 <Id>413</Id>
 <IdOld>0</IdOld>
 <RowsAffected>1</RowsAffected>
 <StoreDescription></StoreDescription>
 <StoreDetail>0</StoreDetail>
 <StoreResult>srInserted</StoreResult>
</EoStoreResult>
</_TEoListBase_Items>
</EoStoreResultList>
```

After a successfull increase the node **StoreResult** will have the value *srInserted*. If an error occurred during the increase, the node **StoreResult** will have the value *srError*. The error description will be sent with the **StoreDescription** node.

---

## Change Orders - Informatie voor ontwikkelaars - MendriX Support & Documentatie

_Bron: https://support.mendrix.nl/space/API/93881088/Change+Orders_

# Change Orders

## Steps

To change a order in MendriX TMS using module Custom Link, follow the next steps.

> For other (important) information, always read [Getting Started](/space/API/93881066) first.​

- Connect module Custom Link.
- First request the most recent copy of a single order using the [Request Order by Id](/space/API/93881100) command.
- Now change the received XML to meet the requirements of the wanted changes.

  > Note that **not all data of invoiced orders can be changed**. Product and article data can not be changed. They are fixed by the invoice created. They can only be changed when the invoice is removed or cancelled. When changed products or article data is send of an invoiced order, these changes will be ignored.

> Note also that orders that have been invoiced before, but the invoice are deleted will not automaticly update their article values/numbers anymore. This can be changed by setting the **NumberManual** and **PriceManual** properties to False.

- Now send the EoCustomLinkStoreOrdersNormal command containing this changed XML. If the order hasn't been requested first, the store will be rejected.
- After processing you receive the EoStoreResultList response or possibly the [errors](/space/API/93881066) response.
- Disconnect module Custom Link.

## Applying settings

It's possible to let Custom Link apply settings as configured in MendriX. To do this, use the field EoCustomLinkStoreOrdersNormal.ApplyImportSettings. This has the following effects:

- OrderId is copied to OrderReference if OrderReference isn't speficied in the request, and setting WorldLink.CopyOrderIdToReference=True.
- TimeWindows are tasks are update based on the settings of the product.
- The order is automatically confirmed (preplanned-flag is unset), if setting Orders.DefaultConfirmOrdSub=1.
- Automatic invoice description of the order is enabled or disabled based on setting Orders.DefaultAutoInvoiceDescriptionEnabled.
- If no categories are specified in the request, the categories are changed to the categories as specified in the relation.
- The way the distance/duraction is calculated is changed based on setting Distances.KmsCalcTaskCircle.
- If no start and end address are specified in the request, these are entered based on start and end address from the relation or the administration of the relation.
- If no country is specified for the tasks, the default country is entered, based on setting General.DefaultCountry.
- Goods are split in separate lines, when goods with multiple parts are specified in the request (based on setting WorldLink.GoodsRowsOrPartsCount).
- If the order has tasks but no goods, one good is added automatically.

## Changing invoiced orders

### Articles can't be modified, added, removed

Invoiced order can be fully modified, except for its articles. No articles can be added, remove or changed.

The product can be changed, but the articles are untouched. So articles in the order will not be overwritten by the articles of the product.

### InvoiceStatus can be changed, but has no effect on the invoices or creditinvoices

Also the InvoiceStatus can be changed, but will have no effect until the invoice is either deleted or cancelled, thus freeing the order again. When trying to create invoices again, the order without InvoiceStatus=2 will be excluded from the invoice.

While invoiced, an order MendriX will have Invoice status 'on invoice', because it has an invoice key, not because of InvoiceStatus. So changing the invoice status will not have any effect visually either.

If InvoiceSatus is changed it will also have no effect on credit invoices created from the invoiced orders. All orders will be credited.

### Example Files

```
\Bin\Metadata\EoCustomLinkStoreOrdersNormal.xml
\Bin\Metadata\EoStoreResultList.xml
```

---

## Create Clients - Informatie voor ontwikkelaars - MendriX Support & Documentatie

_Bron: https://support.mendrix.nl/space/API/93881089/Create+Clients_

# Create Clients

Creating new clients in the storage, is done with the same command as "Changing Clients", but with negative identifiers.

> For other (important) information, always read [Getting Started](/space/API/93881066) first.

---

## Request Questionnaire by TaskId - Informatie voor ontwikkelaars - MendriX Support & Documentatie

_Bron: https://support.mendrix.nl/space/API/93881090/Request+Questionnaire+by+TaskId_

# Request Questionnaire by TaskId

Requesting orders from MendriX TMS is achieved by the following steps.

> For other (important) information, always read [Getting Started](/space/API/93881066) first.

## How To Request A Questionnaire By Its TaskId

## Step 1 - Connect

Connect module Custom Link.

## Step 2 - Request Data Of Orders

​Next send the request to retrieve a few orders by specifying the exact TaskId(s).

```xml
<?xml version="1.0" encoding="windows-1252"?>
<EoCustomLinkRequestTaskQuestionnaire Type="TEoCustomLinkRequestTaskQuestionnaire" xsi:noNamespaceSchemaLocation="GdxEoStructures.xsd" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
 <KeysExplicitAsCsv>437,438</KeysExplicitAsCsv>
</EoCustomLinkRequestTaskQuestionnaire>
```

## Step 3 - Receive Response With Data

Receive the response containing the whole XML of the matching questionnaires. Each questionnaire has the TaskId and XML.

```xml
<?xml version="1.0" encoding="windows-1252"?>
<EoCustomLinkResponseTaskQuestionnaire Type="TEoCustomLinkResponseTaskQuestionnaire" xsi:noNamespaceSchemaLocation="GdxEoStructures.xsd" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
<Data Type="TEoCustomLinkTaskQuestionnaireList">
<_TEoListBase_Items>
<EoCustomLinkTaskQuestionnaire Type="TEoCustomLinkTaskQuestionnaire">
 <TaskId>437</TaskId>
 <XML><questionnaireReport>
                           <questionnaireId>CUTK-SUCCEED</questionnaireId>
                           <questionnaireVersion>2</questionnaireVersion>
                           <timestamp>2015-10-05T15:14:41Z</timestamp>
                           <answer>
                             <questionId>TERMINAL</questionId>
                             <answerOptionId>1</answerOptionId>
                           </answer>
                           <answer>
                             <questionId>CONTAINER</questionId>
                             <loops>
                               <loop>
                                 <answer>
                                   <questionId>CONTAINER</questionId>
                                   <answerValue>G</answerValue>
                                 </answer>
                               </loop>
                             </loops>
                           </answer>
                           <answer>
                             <questionId>PAUZE</questionId>
                             <answerOptionId>1</answerOptionId>
                           </answer>
                           <answer>
                             <questionId>MINUTEN_PAUZE</questionId>
                             <answerValue>55</answerValue>
                           </answer>
                         </questionnaireReport></XML>
</EoCustomLinkTaskQuestionnaire>
<EoCustomLinkTaskQuestionnaire Type="TEoCustomLinkTaskQuestionnaire">
 <TaskId>438</TaskId>
 <XML><questionnaireReport>
                           <questionnaireId>CUTK-SUCCEED</questionnaireId>
                           <questionnaireVersion>2</questionnaireVersion>
                           <timestamp>2015-12-07T12:10:01Z</timestamp>
                           <answer>
                             <questionId>TERMINAL</questionId>
                             <answerOptionId>5</answerOptionId>
                           </answer>
                           <answer>
                             <questionId>CONTAINER</questionId>
                             <loops>
                               <loop>
                                 <answer>
                                   <questionId>CONTAINER</questionId>
                                   <answerValue>8</answerValue>
                                 </answer>
                               </loop>
                             </loops>
                           </answer>
                           <answer>
                             <questionId>PAUZE</questionId>
                             <answerOptionId>1</answerOptionId>
                           </answer>
                           <answer>
                             <questionId>MINUTEN_PAUZE</questionId>
                             <answerValue>55</answerValue>
                           </answer>
                         </questionnaireReport></XML>
</EoCustomLinkTaskQuestionnaire>
</_TEoListBase_Items>
</Data>
</EoCustomLinkResponseTaskQuestionnaire>
```

## Step 4 - Disconnect

Disconnect module Custom Link.

## Example Files

```
\Bin\Metadata\EoCustomLinkRequestTaskQuestionnaire.xml
\Bin\Metadata\EoCustomLinkResponseTaskQuestionnaire.xml
```

---

## Request Invoices - Informatie voor ontwikkelaars - MendriX Support & Documentatie

_Bron: https://support.mendrix.nl/space/API/93881091/Request+Invoices_

# Request Invoices

## Steps

It is possible to request invoices from Custom Link which match specified criteria. Steps:

- Connect module Custom Link.
- Send a EoCustomLinkRequestInvoices XML request.
- Receive the EoCustomLinkResponseInvoices XML response.
- Disconnect module Custom Link

## Example Files

```
\Bin\Metadata\EoCustomLinkRequestInvoices.xml
\Bin\Metadata\EoCustomLinkResponseInvoices.xml
```

---

## Request Rides (compact) - Informatie voor ontwikkelaars - MendriX Support & Documentatie

_Bron: https://support.mendrix.nl/space/API/93881092/Request+Rides+(compact)_

# Request Rides (compact)

## Request

```xml
<?xml version="1.0" encoding="windows-1252"?>
<EoCustomLinkRequestRidesCompact Type="TEoCustomLinkRequestRidesCompact" xsi:noNamespaceSchemaLocation="GdxEoStructures.xsd" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <Nested>False</Nested>
  <Filter Type="TEoFilterPlannerMaster">
    <PeriodBegin>0</PeriodBegin>
    <PeriodEnd>0</PeriodEnd>
    <JobIdsAsCsv>10</JobIdsAsCsv>
    <RideName>Henk</RideName>
  </Filter>
</EoCustomLinkRequestRidesCompact>
```

## Response

```xml
<?xml version="1.0" encoding="windows-1252"?>
<EoCustomLinkResponseRidesCompact Type="TEoCustomLinkResponseRidesCompact">
  <Data Type="TEoCustomLinkRideCompactList">
    <_TEoListBase_Items>
      <EoCustomLinkRideCompact Type="TEoCustomLinkRideCompact">
        <Id>4</Id>
      </EoCustomLinkRideCompact>
    </_TEoListBase_Items>
  </Data>
</EoCustomLinkResponseRidesCompact>
```

Compact ride for now only contains the Id, but eventually planning-fields (OperatorId, VehicleId, MaterialId) will be added.

Rides can only be requested via socket, not via soap because of different client related information a ride can contain

---

## Request Job Progress - Informatie voor ontwikkelaars - MendriX Support & Documentatie

_Bron: https://support.mendrix.nl/space/API/93881093/Request+Job+Progress_

# Request Job Progress

## Request

```xml
<?xml version="1.0" encoding="windows-1252"?>
<EoCustomLinkRequestJobProgress Type="TEoCustomLinkRequestJobProgress">
    <Nested>False</Nested>
    <Filter Type="TEoKeyInt">
        <Id>6</Id>
    </Filter>
</EoCustomLinkRequestJobProgress>
```

## Response

```xml
<?xml version="1.0" encoding="windows-1252"?>
<EoCustomLinkResponseJobProgress Type="TEoCustomLinkResponseJobProgress">
    <Data Type="TEoCustomLinkJobProgress">
        <StatusId>3</StatusId>
        <JobId>6</JobId>
        <Progress Type="TEoJobProgressOrderImport">
            <RowCount>15</RowCount>
            <RowCurrent>12</RowCurrent>
            <RetryCount>1</RetryCount>
        </Progress>
    </Data>
</EoCustomLinkResponseJobProgress>
```

STATUS_UNDEFINED = 0; STATUS_PENDING = 1; STATUS_WORKING = 2; STATUS_COMPLETED = 3; STATUS_CANCELLED = 4; STATUS_WARNING = 5; STATUS_ERROR = 6;

---

## Store Ride Timewindow - Informatie voor ontwikkelaars - MendriX Support & Documentatie

_Bron: https://support.mendrix.nl/space/API/93881094/Store+Ride+Timewindow_

# Store Ride Timewindow

## Request

```xml
<?xml version="1.0" encoding="windows-1252"?>
<EoCustomLinkStoreRideTimeWindows Type="TEoCustomLinkStoreRideTimeWindows" >
  <JobInfoOrderImport Type="TEoCustomLinkJobInfoOrderImport">
    <JobId>20</JobId>
    <RowIdsCsv>1</RowIdsCsv>
  </JobInfoOrderImport>
  <Data Type="TEoCustomLinkRideTimeWindowList">
    <_TEoListBase_Items>
      <EoCustomLinkRideTimeWindow Type="TEoCustomLinkRideTimeWindow">
        <Id>11</Id>
        <MomentStart>2015-08-26T10:00:00</MomentStart>
        <MomentEnd>2015-08-26T22:00:00</MomentEnd>
      </EoCustomLinkRideTimeWindow>
    </_TEoListBase_Items>
  </Data>
</EoCustomLinkStoreRideTimeWindows>
```

---

## Request Employees - Informatie voor ontwikkelaars - MendriX Support & Documentatie

_Bron: https://support.mendrix.nl/space/API/93881095/Request+Employees_

# Request Employees

## Steps

It is possible to request employees from Custom Link which match specified criteria. The following files contain examples of a request and a response.

- Connect module Custom Link.
- Send a EoCustomLinkRequestEmployees XML request.
- Receive the EoCustomLinkResponseEmployees XML response.
- Disconnect module Custom Link

> For other (important) information, always read [Getting Started](/space/API/93881066) first.

## Example Files

```
\Bin\Metadata\EoCustomLinkRequestEmployees.xml
\Bin\Metadata\EoCustomLinkResponseEmployees.xml
```

---

## Requesting Date+Time - Informatie voor ontwikkelaars - MendriX Support & Documentatie

_Bron: https://support.mendrix.nl/space/API/93881096/Requesting+Date+Time_

# Requesting Date+Time

## Steps

> For other (important) information, always read [Getting Started](/space/API/93881066) first.

To request the current date and time from Custom Link, send the following frame to Custom Link, followed by a single Char(0).

```
<EoCustomLinkRequestDateTime Type="TEoCustomLinkRequestDateTime">
</EoCustomLinkRequestDateTime>
```

The response you will get, will be something like the following, again null-terminated by a Char(0).

```
<EoCustomLinkResponseDateTime Type="TEoCustomLinkResponseDateTime">
 <DateTime>2008-08-12T18:16:14</DateTime>
</EoCustomLinkResponseDateTime>
```

## Example Files

The previous request and response examples can be found in the following files.

```
Bin\Metadata\EoCustomLinkRequestDateTime.xml
Bin\Metadata\EoCustomLinkResponseDateTime.xml
```

---

## Create Employees - Informatie voor ontwikkelaars - MendriX Support & Documentatie

_Bron: https://support.mendrix.nl/space/API/93881097/Create+Employees_

# Create Employees

Creating new employees in the storage, is done with the same command as "Changing Employees", but with negative identifiers.

> For other (important) information, always read [Getting Started](/space/API/93881066) first.

---

## Store Measurement - Informatie voor ontwikkelaars - MendriX Support & Documentatie

_Bron: https://support.mendrix.nl/space/API/93881098/Store+Measurement_

# Store Measurement

## How To Store a Measurement

Storing measurements in MendriX TMS is achieved by the following steps.

> For other (important) information, always read [Getting Started](/space/API/93881066) first.

## Step 1 - Connect

Connect module Custom Link.

## Step 2 - Send Measurement Data

```xml
<?xml version="1.0" encoding="windows-1252"?>
<EoCustomLinkStoreMeasurements Type="TEoCustomLinkStoreMeasurements" xsi:noNamespaceSchemaLocation="GdxEoStructures.xsd" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <Data Type="TEoCustomLinkMeasurementList">
    <_TEoListBase_Items>
      <EoCustomLinkMeasurement Type="TEoCustomLinkMeasurement">
        <SensorCode>2</SensorCode>
        <MaterialId>1</MaterialId>
        <MeasurementTypeId>0</MeasurementTypeId>
        <Measurement>7.92</Measurement>
        <Moment>2016-11-24T10:30:00</Moment>
      </EoCustomLinkMeasurement>
      <EoCustomLinkMeasurement Type="TEoCustomLinkMeasurement">
        <SensorCode>1</SensorCode>
        <MaterialId>2</MaterialId>
        <MeasurementTypeId>0</MeasurementTypeId>
        <Measurement>8.13</Measurement>
        <Moment>2016-11-24T10:29:00</Moment>
      </EoCustomLinkMeasurement>
    </_TEoListBase_Items>
  </Data>
</EoCustomLinkStoreMeasurements>
```

## Step 3 - Receive Response With Data

Receive the response containing the StoreResults. If there is no sensor for the vehicle, the measurement is ditched.

If the measurement is ditched, one result with srError is returned. If the measurement is stored, a result for the corresponding Position-store is given, followed by the result for the Measurement-store.

```xml
<?xml version="1.0" encoding="windows-1252"?>
<EoStoreResultList Type="TEoStoreResultList">
<_TEoListBase_Items>
<EoStoreResult Type="TEoStoreResult">
 <Id>15</Id>
 <IdOld>0</IdOld>
 <RowsAffected>1</RowsAffected>
 <StoreDescription></StoreDescription>
 <StoreDetail>0</StoreDetail>
 <StoreResult>srInserted</StoreResult>
 <ErrorType>etNone</ErrorType>
</EoStoreResult>
<EoStoreResult Type="TEoStoreResult">
 <Id>12</Id>
 <IdOld>0</IdOld>
 <RowsAffected>1</RowsAffected>
 <StoreDescription></StoreDescription>
 <StoreDetail>0</StoreDetail>
 <StoreResult>srInserted</StoreResult>
 <ErrorType>etNone</ErrorType>
</EoStoreResult>
<EoStoreResult Type="TEoStoreResult">
 <Id>1</Id>
 <IdOld>0</IdOld>
 <RowsAffected>0</RowsAffected>
 <StoreDescription>Measurement ditched, no sensor found for vehicle 2, sensorcode 1</StoreDescription>
 <StoreDetail>0</StoreDetail>
 <StoreResult>srError</StoreResult>
 <ErrorType>etUnknown</ErrorType>
</EoStoreResult>
</_TEoListBase_Items>
</EoStoreResultList>
```

## Step 4 - Disconnect

Disconnect module Custom Link.

## Example Files

```
\Bin\Metadata\EoCustomLinkStoreMeasurement.xml
\Bin\Metadata\EoStoreResultList.xml
```

---

## Activate Order Template - Informatie voor ontwikkelaars - MendriX Support & Documentatie

_Bron: https://support.mendrix.nl/space/API/93881099/Activate+Order+Template_

# Activate Order Template

## Request

```xml
<?xml version="1.0" encoding="windows-1252"?>
<EoCustomLinkActivateOrderTemplate Type="TEoCustomLinkActivateOrderTemplate" xsi:noNamespaceSchemaLocation="GdxEoStructures.xsd" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
    <Data Type="TEoActivateOrderTemplateRequest">
        <TaskRequestedMoment>2017-10-28T13:30:00</TaskRequestedMoment>
        <TaskType>2</TaskType>
        <Address Type="TEoAddress">
            <Name>Team2000</Name>
            <Premise></Premise>
            <Street>Vleugtweg</Street>
            <Number>22</Number>
            <PostalCode>3111</PostalCode>
            <Place>Rotselaar</Place>
            <State></State>
            <Country>Belgie</Country>
            <CountryCode>BE</CountryCode>
        </Address>
    </Data>
</EoCustomLinkActivateOrderTemplate>
```

Custom Link will look for a template that has a task with the specified tasktype (get=1, bring=2) for the specified address and a requested timewindow in which the time-part of TaskRequestedMoment would occur. This template will be activated on a date, so that TaskRequestedMoment (date and time) will occur within the requested timewindow of the task, but only if the template is repeated on this day.

You can also specify TaskRequestedDate instead of TaskRequestedMoment. In that case, the template will be activated on a date, so that the requested timewindow of the task starts on (the date part of) TaskRequestedDate, also only if the template is repeated on this day.

> If there are more than one matching templates, all these templates will be activated. If one template has two matching tasks on two days, the same template will be activated twice.

> Address will match if the following fields are the same: country or countrycode, state, place, postalcode, street and number. All characters other than letters (a-z and A-Z) and numbers (0-9) are stripped, and lowercase letters will be considered equal to uppercase letters. Example: Postalcode 3605 LW would be the same as 3605lw.

## Example

Consider the following template:

Ordermoment: 2011-01-01 12:00. Repeat on days: Thursday, Friday   Task 1: requested from 2011-01-02 12:00 until 13:00, get-task Task 2: requested from 2011-01-03 14:00 until 15:00, bring-task

Now consider a request with the address of Task 2, TaskType=2 and TaskRequestedMoment=2017-11-05 14:30. Task 2 is a bring-task, and 14:30 is within the timewindow of Task 2. The ordermoment is two days before the requested timewindow of Task 2, so the resulting order would have an ordermoment of 2017-11-03 12:00. 2017-11-03 is a friday, so the template can be copied. The resulting order would look like this:

Ordermoment: 2017-11-03 12:00. Task 1: requested from 2017-11-04 12:00 until 13:00, get-task Task 2: requested from 2017-11-05 14:00 until 15:00, bring-task

For the same request, but with TaskRequestedMoment=2017-11-06 14:30, the template would not be activated, because the resulting order would be on saturday and the template is not repeated on saturday.

For the same request, but with TaskRequestedMoment=2017-11-05 15:30, the template would not be activated, because 15:30 is not in the timewindow of Task 2.

For the same request, but with TaskType=1, the template would not be activated, because Task 2 is a bring-task..

For the same request, but with TaskRequestedDate=2017-11-05, the template would be activated the same way as in the example.

> For other (important) information, always read [Getting Started](/space/API/93881066) first.

## Response

```xml
<?xml version="1.0" encoding="windows-1252"?>
<EoStoreResultList Type="TEoStoreResultList" xsi:noNamespaceSchemaLocation="GdxEoStructures.xsd" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
    <_TEoListBase_Items>
        <EoStoreResult Type="TEoStoreResult">
            <Id>224</Id>
            <IdOld>0</IdOld>
            <StoreResult>srInserted</StoreResult>
            <ErrorType>etNone</ErrorType>
        </EoStoreResult>
    </_TEoListBase_Items>
</EoStoreResultList>
```

The storeresult will contain the Ids of the resulting orders. If the list is empty, no templates have been activated.

## Example Files

```
\Bin\Metadata\EoCustomLinkActivateOrderTemplate_ByMoment.xml
\Bin\Metadata\EoCustomLinkActivateOrderTemplate_ByDate.xml
\Bin\Metadata\EoStoreResultList.xml
```

---

## Request Order by Id - Informatie voor ontwikkelaars - MendriX Support & Documentatie

_Bron: https://support.mendrix.nl/space/API/93881100/Request+Order+by+Id_

# Request Order by Id

## How To Request An Order By It's Id

Requesting orders from MendriX TMS is achieved by the following steps.

> For other (important) information, always read [Getting Started](/space/API/93881066) first.

## Step 1 - Retrieve the Id's of The Wanted Orders

First [request the order Id's](/space/API/93881074) of the orders that meet your requirements (e.g. the order Id of the order with a specific barcode). Requesting only the Id's first reduces the load on heavy duty machines a lot.

## Step 2 - Connect

Connect module Custom Link.

## Step 3 - Request Data Of Orders

Next send the request to retrieve a few orders by specifying the exact Id(s). (Don't request too many orders at once. Experiment with the server load and response time to find the right amount. If possible, request orders one by one.)

```xml
<?xml version="1.0" encoding="windows-1252"?>
<EoCustomLinkRequestOrdersNormal Type="TEoCustomLinkRequestOrdersNormal" xsi:noNamespaceSchemaLocation="GdxEoStructures.xsd" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <Nested>False</Nested>
  <Filter Type="TEoFilterOrdersNormal">
    <KeysExplicitAsCsv>120,121,122,123,124</KeysExplicitAsCsv>
  </Filter>
</EoCustomLinkRequestOrdersNormal>
```

## Step 4 - Receive Response With Data

The receive the response containing the whole XML of the matching orders.

```xml
<?xml version="1.0" encoding="windows-1252"?>
<EoCustomLinkResponseOrdersNormal Type="TEoCustomLinkResponseOrdersNormal">
<Data Type="TEoOrderMxList">
..
</Data>
</EoCustomLinkResponseOrdersNormal>
```

## Step 5 - Disconnect

Disconnect module Custom Link.

# Example Files

```
\Bin\Metadata\EoCustomLinkRequestOrdersNormalxml
\Bin\Metadata\EoCustomLinkResponseOrdersNormal.xml
```

---

## Change Employees - Informatie voor ontwikkelaars - MendriX Support & Documentatie

_Bron: https://support.mendrix.nl/space/API/93881101/Change+Employees_

# Change Employees

## Steps

To change an employee in MendriX TMS through module Custom Link, follow the next steps.

> For other (important) information, always read [Getting Started](/space/API/93881066) first.

- Connect module Custom Link.
- First request the original XML to not overwrite or empty any fields later on, using the [Request Employees](/space/API/93881095) command.
- Take the XML you received of the employee, change the appropriate fields according to wishes.
- Now send the below EoCustomLinkStoreEmployees command, with the full changed XML in it.
- Now you receive a EoStoreResultList or an error to indicate the success.
- Disconnect module Custom Link.

## Example Files

```
\Bin\Metadata\EoCustomLinkStoreEmployees.xml
\Bin\Metadata\EoStoreResultList.xml
```

---

## Change Clients - Informatie voor ontwikkelaars - MendriX Support & Documentatie

_Bron: https://support.mendrix.nl/space/API/93881102/Change+Clients_

# Change Clients

## Steps

To change a client in MendriX TMS using model Custom Link, follow the next steps.

> For other (important) information, always read [Getting Started](/space/API/93881066) first.

- Connect module Custom Link.
- First request the most recent copy of a single Client using the [Request Client by Id](/space/API/93881077) command.
- Now change the received XML to meet the requirements of the wanted changes.
- Now send the EoCustomLinkStoreClients command containing this changed XML.
- After processing you receive the EoStoreResultList response or possibly the [errors](/space/API/93881066) response.
- Disconnect module Custom Link.

## Example Files

```
\Bin\Metadata\EoCustomLinkStoreClients.xml
\Bin\Metadata\EoStoreResultList.xml
```

---

## Keep Alive - Informatie voor ontwikkelaars - MendriX Support & Documentatie

_Bron: https://support.mendrix.nl/space/API/93881103/Keep+Alive_

# Keep Alive

## Usage

Connections with Custom Link are automatically terminated after five minutes of inactivity, to prevent unnecessary use of resoures. In some cases however, keeping the connection open results in significant performance gain. Use the Keep Alive command every few minutes (before the time-out of five minutes expires), to keep the connection active.

## Example files

```
\Bin\Metadata\EoCustomLinkRequestKeepAlive.xml
\Bin\Metadata\EoCustomLinkResponseStayingAlive.xml
```

---

## In Depth Technical - Informatie voor ontwikkelaars - MendriX Support & Documentatie

_Bron: https://support.mendrix.nl/space/API/93881104/In+Depth+Technical_

# In Depth Technical

## Compatibility

Future versions of Custom Link may change in working. Especially during pilot phases functionality may change in a lesser or more extent. However, it's likely changes are a lot less frequent than changes to the database and the inner workings of MendriX. This is why the layer of abstraction Custom Link offers, is an advantage for programming a link between MendriX and third party software.

## Expertise

When using Custom Link on a technical level, a certain amount of background knowledge is necessary. The depth of this knowledge depends on the needed results and the technology needed to bring those results.

The XML specified in this chapter, may be transformed, generated and interpreted for different purposes using conventional programming languages in combination with a DOM. Depending on the needs, it's also possible to use common modern technology like XPath, XSLT and XQuery. The formats of the XML used in MendriX are described in XSD files.

> One of the best XML/XSD/XSLT editing tools is Altova XmlSpy. It provides an intuitive user interface and snappy response, even with larger XML documents.

Definitions (search Internet for more detailed information):

- **DOM** (The Document Object Model) is a platform- and language-independent standard object model for representing HTML or XML and related formats.

- **XPath** (XML Path Language) is a language for selecting nodes from an XML document. In addition, XPath may be used to compute values (strings, numbers, or boolean values) from the content of an XML document.

- **XSLT** (Extensible Stylesheet Language Transformations) is an XML-based language used for the transformation of XML documents into other XML or "human-readable" documents. The original document is not changed; rather, a new document is created based on the content of an existing one. The new document may be serialized (output) by the processor in standard XML syntax or in another format, such as HTML or plain text. XSLT is most often used to convert data between different XML schema's or to convert XML data into HTML or XHTML documents for web pages.

- **XQuery** is a query language (with some programming language features) that is designed to query collections of XML data. It is semantically similar to SQL.

- **XSD** files express a XML schema: a set of rules to which an XML document must conform in order to be considered 'valid' according to that schema. However, unlike most other schema languages, XSD was also designed with the intent that determination of a document's validity would produce a collection of information adhering to specific data types. Such a post-validation infoset can be useful in the development of XML document processing software. An XML Schema Definition (XSD) typically has the filename extension ".xsd". The language itself is sometimes informally referenced as XSD. XSD is also an initialism for XML Schema Datatypes, the datatype portion of XML Schema.

An understanding of TCP/IP is assumed to ensure correct communication between Custom Link and a third party. Where possible, background information and pointers are given for the best usage of this technology.

## Server Load

It is very important to measure or calculate the server load a third party link is going to cause during peak operations. The link itself must ensure a sensible spreading of load to the system as a whole. Spreading load by requesting and storing data in small portions (for example per day, per hour, per order) is better than causing lots of processing at once by sending big tasks as one request. It is generally also a good idea to prevent 'hammering' requests. Provide some 'idle' time between multiple requests for retrieving and changing data to unburden the system and provide processing power to lower priority system tasks.

### Using sequences when requesting orders

When requesting orders you can specify a minimum sequence to limit the number of orders returned by your request, thereby lowering the server load. Click here for more information about using sequences.

## Security

Module Custom Link offers an open interface. By default it can only be connected from a source within the same computer (localhost). The third party link that communicates with Custom Link is responsible for providing enough security.

It is not recommended to configure Custom Link to accept connections from other interfaces than localhost. The security of the system might be compromised if done so. Sources from outside the computer may connect and use the possibilities of Custom Link in undesired ways. Such outside connections can be offered safely however, by letting the third party middle-ware connect locally and letting it offer an external interface. This external interface, should be protected with trustworthy authentication methods.

Custom Link itself does not offer authentication or security restrictions. The developed third party link should take care of shielding information and limiting processing actions of data by unauthorized sources. Both actions by itself and by unknown external applications should be taken in consideration.

## Communication

Module Custom Link listens on a TCP/IP socket. The host address and the port are configurable. There is virtually no limit to the concurrent amount of connections, except by the limitations of the used hardware and operating system. The module communicates with blocks of information, called 'frames'. Each frame is null-terminated and must end with a Char(0).

> TCP/IP only guarantees the order and the arrival of data, as long as a connection exists. It is not guaranteed that transmitted data is received in the same parts as they are send. Parts can arrive concatenated or cut into multiple parts. Most wrapper implementations however, provide functionality to read data as a whole frame again. This might be a routine which reads data until a specified end-character is found in the stream, like a Char(0).

Each frame contains one XML structure or a special command. This is the same for both directions of the communication. Of an XML frame, the first character must always be a '<' (without quotes). A special command starts with a different character.

> Unknown XML-frames, notifications or special commands must be ignored as much as possible by both sides of the communication. This is to be as much forward compatible as possible with future extensions. The same goes for unknown XML elements and attributes.

The processing of commands happens sequentially. This means that the answers will be sent back in the same order in which the commands arrived. The communication is a-synchronous however. This means multiple commands may be transmitted sequentially, without waiting for the responses. It is also possible that Custom Link sends a notification before an answer is send back after receiving a command.

It is allowed to keep a connection open during a longer period of time to send multiple commands and receive the responses. The alternative is to make a connection for each command and close the connection after the response is received. The latter might be a more convenient way of programming, because it may reduce the amount of connections to maintain and the overhead needed to monitor the health of connections and reinitialize when needed. Custom Link might disconnect a connection if it is idle too long, or if an exception occurs during the processing. The user of a connection must take this into account and take appropriate counter measurements.

## Encoding

At the moment the encoding of XML used by MendriX is 'windows-1252'. It conforms to XML version 1.0 for non-printable characters. Char(0) however is not fully supported for it indicates an end of line.

> Note: 'windows-1252' is a character encoding used by many European languages. In LaTeX packages, it is referred to as ansinew. The encoding is a superset of ISO 8859-1. It is IANA-approved. It also supports all characters in ISO 8859-15, though some are mapped to different code points, thus not compatible.

The encoding is not always in the header of an XML frame from MendriX, but if it is omitted then 'windows-1252' applies. For third party middleware requiring the explicit specification of encoding, set the DOM correctly or add the following line explicitly.

```
<?xml version="1.0" encoding="Windows-1252"?>
```

> It is possible that future versions of MendriX will add or change this header itself. It is possible for example that in the future UTF-8 will be used. To stay as compatible as possible with future versions, the non-existence of a header should be confirmed before adding an encoding line yourself.

As being windows-1252 and XML 1.0 compliant, the five standard XML placeholders are supported and the necessary characters are encoded as their numeric representation like .

```
&amp; & ampersand
&lt; < less than
&gt; > greater than
&apos; ' apostrophe
&quot; " quotation mark
```

## Dates and Times

Custom Link uses ISO-8601 formats of dates and times in its XML. However a few parts of those specifications are not completely fixed in definition. In this documentation we describe the absolute definition which MendriX uses.

MendriX returns a date and time in one single format. The following first example shows 31st of december in 2011 in the evening with 22:23:24 o' clock in local-time. The local time zone offset is +02:00 hours compared to UTC (also called Zulu-time). This means the second line is the equivalent absolute moment in time. The third line is the short version of the second line, directly indicating Zulu-time is given. Zulu time is another name for UTC.

```
<SomeDateTime>2011-12-31T22:23:24+02:00</SomeDateTime>
<SomeDateTime>2011-12-31T20:23:24+00:00</SomeDateTime>
<SomeDateTime>2011-12-31T20:23:24Z</SomeDateTime>
```

Mind that when the time-zone or Zulu-indicator ('Z') are not specified, then MendriX assumes a date and time are given in the context of the current time-zone and also with the current DST (day light savings bias) that applies for that given date and time. For MendriX this means that the following two examples are equivalent when provided in The Netherlands during the summer when DST applies. Mind the absence of the Zulu-indicator 'Z', because we are specifying local time.

```
<SomeDateTime>2011-06-25T20:23:24+02:00</SomeDateTime>
<SomeDateTime>2011-06-25T20:23:24</SomeDateTime>
```

The same applies for the following two examples when provided in The Netherlands during the winter when DST applies.

```
<SomeDateTime>2011-12-25T20:23:24+01:00</SomeDateTime>
<SomeDateTime>2011-12-25T20:23:24</SomeDateTime>
```

Note the +01:00 during the winter, where +02:00 is applied during the summer.

For more references and background information see also: http://en.wikipedia.org/wiki/ISO_8601 and http://www.w3.org/TR/xmlschema11-2/ .

MendriX also supports a legacy datetime type of node. This type is more of a legacy format, which consists of a floating point value representing the number of days that have passed since 12/30/1899. The fractional part of the value is the fraction of a 24 hour day that has elapsed. Following are some examples: 

```
<SomeDateTime>0</SomeDateTime>
meaning: 12/30/1899 12:00 am
<SomeDateTime>2.75</SomeDateTime>
meaning: 1/1/1900 6:00 pm   
<SomeDateTime>-1.25</SomeDateTime>
meaning: 12/29/1899 6:00 am   
<SomeDateTime>35065 </SomeDateTime>
meaning: 1/1/1996 12:00 am
```

## Identifiers

Read the XSD description of TEoKeyIntInfraMx carefully, to understand the working of local and global identifiers in MendriX. <Id> always contains the local identifier. This is the identifier in the database this Custom Link is connected to. When `Id` is negative, MendriX assumes this is new data to be freshly inserted in the database. After inserting this new data, the resulting local Id's are return in the TEoStoreResultList. When a positive value was specified, the data is updated and must be existing.

Normally only the <Id> of an item has to be specified. Keep the value of CreatorGuid and OriginalId:

```
<CreatorGuid Type="TEoPropertyGuid">
  <AsString>{00000000-0000-0000-0000-000000000000}</AsString>
</CreatorGuid>
<OriginalId>0</OriginalId>
```

These combined are the global indentifier of the same data in another database. This is only needed to synchronize different MendriX systems and not commonly used.

```
      <OrderId Type="TEoKeyIntInfraMx">
        <Id>-229</Id>
        <CreatorGuid Type="TEoPropertyGuid">
          <AsString>{00000000-0000-0000-0000-000000000000}</AsString>
        </CreatorGuid>
        <OriginalId>0</OriginalId>
        <Revision>1</Revision>
        <Sequence>47</Sequence>
        <Synchronized>False</Synchronized>
        <ToucherGuid Type="TEoPropertyGuid">
          <AsString>{00000000-0000-0000-0000-000000000000}</AsString>
        </ToucherGuid>
        <Data></Data>
      </OrderId>
```

## Tip: Automatically Creating Filter Node XML

Tip: MendriX itself can generate the filter node XML. This works for any filter/search details Window in a MendriX sections. For orders/shipments for example, follow the next steps: via the main window | section orders | Search button | Advanced search | change the wanted settings | press Ctrl+Shift+C >> now a message appears notifying that the whole XML of the filter is on the Windows clipboard.

---

## Important Basics - Informatie voor ontwikkelaars - MendriX Support & Documentatie

_Bron: https://support.mendrix.nl/space/API/93881105/Important+Basics_

# Important Basics

## Connecting with Custom Link

There are two ways to connect with Custom Link: using a raw socket connection, and using a SOAP connection.

### TCP/IP Raw Socket Connection

Create a plain TCP/IP socket and connect with the address and port of Custom Link. Custom Link now waits for requests to give a response to. To be more robust, it's recommended to open a new connection for each separate request and close it again after receiving a full repsonse, though multiple requests and responses during one session is allowed. Parallel connections are also supported by module Custom Link.

> On a default installation the IP is 127.0.0.1 (localhost) and the port for Custom Link is 5561.

> Do **never** expose this connection from the outside. The only correct way to use Custom Link from outside your private network is to use SOAP to connect over TLS/SSL. This is secured using API tokens and all commands are available there too.

#### Requests and Responses Null-Terminated

Note that both requests and responses for the TCP/IP Raw Socket Connection are always followed by a Char(0). This means every communication frame you send or receive is null-terminated. When sending a request, module Custom Links starts processing your request as soon as the Char(0) is received. The other way around, you should read any response until you also received the Char(0). Then you may handle the response as a whole.

#### Maximum frame length/size

To prevent choking the communication sockets, the maximum frame length is 5 MB (5*1024*1024 bytes). This is with terminators Char(0) included. Make sure not to request more data than this maximum, and also not to send commands larger than this maximum.

### SOAP Connection

Import the WSDL specifying the offered interface from the following URL:

```
http://ip-adres:port/wsdl/ICustomLinkSoap
```

Then use the following command to perform a Custom Link request:

```
ICustomLinkSoap.ExecuteRequest
```

ExecuteRequest has one parameter containing the request. It returns the response as a string. The request is the same as the request used for the raw socket-connection, but escaped (as defined by XML) and without the terminating Char(0).

For more detailed instructions, see Custom Link and Soap.

## Demo Tool for Experimentation

There is a demonstration application available to develop for Custom Link. It provides XML examples of requests and can send them to Custom Link. First press the "Prepare" button to prepare a request. The XML that appears in the left panel can be altered before sending it. Then press the "Execute" button to send it to Custom Link. The default port and address of Custom Link are used. The response is shown in the right panel.

> This demo tool can be found in the MendriX-installation folder: `\MendriX\Bin\MetaData\DemoCustomLink.exe`.

## XML Schema's with Fields Definitions

Most fields and structures are explained in detail in the following XML schema files.

```
\Bin\Metadata\GdxEoStructures.xsd
\Bin\Metadata\WL_{00000001_00000003}_ORD.xsd
```

Use your favorite XML/XSD tool to inspect and visualize the entity structures in these XSD files. The following image shows an example of two (simple) entities viewed in such a tool.

## Receiving Errors To Your Request

The next file contains a response of Custom Link if a request fails to be processed without errors. Normally Custom Link will restart itself. This is done to re-initalize the module to function well again in case the exception happened due to internal malfunctioning. Textual details of the error will be in the response.

```
\Bin\Metadata\EoCustomLinkException.xml
```

> For full definitions, see the XML Schema file `\MendriX\Bin\Metadata\GdxEoStructures.xsd`.

### Handling errors

Exceptions returned from Custom Link should be handled by the caller. When certain operations fail, they should be retried by the caller to make sure no data gets lost.

### Example: deadlocks

Accidentally Custom Link can deadlock when performing an SQL query on the database. This will resuts in an error like this:

```
EOleException:Transaction (Process ID 68) was deadlocked on lock resources with another process and has been 
chosen as the deadlock victim
```

A deadlock is usually an incident which will not reoccur when the same query is performed again. For errors like this, the caller should resend the request.

## Changing Data

> When storing changes, missing XML fields are going to be cleared in MendriX TMS entities. Make sure also future XML nodes are present in a request to change command. See next instructions on how to prevent losing data.

When changing the data of entities through module Custom link, always first request the full original XML data of an entitity from Custom Link, to make sure you will have all current (and future) fields als values.

- First request the original XML of a single entity, so all fields supported by this version are present with their values.
- Now grap the XML of a single entity (for performance) from the received XML.
- Change the XML of this single entity where wanted. Do not remove any XML nodes, unless you want them cleared.
- Now build the appropriate change request XMLcontaining all of the XML of the changed entity. So also the unchanged fields.
- Send the change request to module Custom Link. Receive the response or an error.

See the Wiki pages of the Commands for more details and examples of how to do this exactly.

> Do not build the XML for changing entitities in the MendriX TMS system manually, because even if it works initially, future versions of MendriX TMS and module Custom Link may add fields which you didn't include in your change requests, thus clearing them and loosing data in the system.

---

## Database direct verbinden - Informatie voor ontwikkelaars - MendriX Support & Documentatie

_Bron: https://support.mendrix.nl/space/API/93881110/Database+direct+verbinden_

# Database direct verbinden

Bedrijven kunnen gebruik maken van directe toegang tot de databases van MendriX. Dit type gebruik wordt niet standaard ondersteund, vanwege de onvoorziene effecten die dit kan hebben.

## Terminologie

**Databases**

Onder databases wordt verstaan de digitale opslag van alle gegevens door de oplossingen van MendriX, zowel in (archief)bestanden met verzamelde gegevens, alsmede gegevens in afzonderlijke bestanden.

**Directe toegang**

Onder directe toegang wordt verstaan het registreren, wijzigen, opvragen, configureren of synchroniseren van zowel de gegevens alsook de structuur daarvan alsook de opslag daarvan, anders dan de daarvoor bedoelde standaard import- en exportmogelijkheden en koppelingsmogelijkheden, zoals via module Custom Link. Dit omvat elke verbindings-, bevragings- of verwerkingsmethode.

## Gratis gebruiksondersteuning

Soms lijkt gebruiksondersteuning te vallen onder het inbegrepen gratis recht binnen de huurovereenkomst of de updateoptie, maar blijkt het later te zijn gevraagd of veroorzaakt door de directe toegang. Dan wordt de ondersteuning alsnog als betaalde consultancy in rekening gebracht. Dit is nodig, omdat MendriX geen enkele invloed kan uitoefenen op de toepassing, noch op de consequenties daarvan.

## Directe toegang versus module Custom Link

Naast de import- en exportmogelijkheden van MendriX en de vele koppelingsmogelijkheden voor standaard producten van derden, zijn er twee manieren om nog geavanceerder te koppelen. Dit zijn module Custom Link of directe toegang tot de database.

Module Custom Link heeft als voordeel dat op de lange termijn veel minder investeringen nodig zijn na het installeren van nieuwe versies van MendriX en dat er op één uniforme manier wordt gekoppeld en kwaliteit bewaakt van prestaties van MendriX. Nog een voordeel is dat investering in ondersteuning meestal veel lager is, omdat er uitgebreide documentatie met voorbeelden wordt meegeleverd.

Directe toegang heeft als voordeel dat de initiële investering en levertijd soms wat lager zijn om een koppeling te realiseren. Ook bestaat dan minder afhankelijkheid van de beschikbare commando's in module Custom Link. Een groot nadeel is het verlies van grip op prestaties. Technisch voorbeeld: Zelfs bij alleen lezen kunnen er grote prestatieproblemen elders in de MendriX oplossingen optreden. Dit komt omdat er 'locks' dienen te worden aangebracht op gegevens, om consistentie bij opvragen tussen entiteiten onderling te garanderen (denk aan totalen en andere redundante gegevens). Het 'lockless' opvragen tast namelijk de integriteit van gegevens aan.

## Module Custom Link

De gewone gebruikersondersteuning kan gratis blijven en de kosten voor modules en oplossingen kunnen lager zijn, doordat voor directe toegang ook module Custom Link afgenomen dient te worden. Dit tegen gangbare tarieven en condities.

Deze module wordt ontwikkeld speciaal om één uniforme manier van koppelen te bieden. Dit zorgt voor een consistente beleving, hoge betrouwbaarheid, hoge borging toekomstmogelijkheden van clouddiensten en microservices, maximalisatie van compatibiliteit in de toekomst en grip op de prestaties van de MendriX oplossingen.

Directe toegang tot databases staat eigenlijk haaks op de filosofie achter module Custom Link om één uniforme en duidelijke koppelingsmogelijkheid te bieden en geeft regelmatig ondersteuningsvraagstukken waarbij vaak in eerste instantie niet (en soms nooit) duidelijk is waar de oorzaak ligt. Genoemde verborgen kosten worden hiermee gedekt en daarnaast wordt het gebruik van module Custom Link gestimuleerd (met alle voordelen van dien).

Module Custom Link wordt geleverd met uitgebreide documentatie, programmeervoorbeelden en de beschikbaarheid voor technische ondersteuning op basis van nacalculatie. Sommige afnemers hebben deze ondersteuning nooit nodig en voldoende aan de documentatie. Sommige afnemers verzoeken technische en functionele ondersteuning van onze implementatieconsultants en/of onze 2e of 3e lijns technische ondersteuning.

## Toekomstbestendigheid

De toekomstbestendigheid van directe toegang tot databases is vele malen kleiner dan het gebruik van module Custom Link. Hoewel deze module ook niet gegarandeerd hetzelfde blijft werken in nieuwe versies, wordt dit altijd getracht en lukt dit in vrijwel alle gevallen. Eigen koppelingen dienen altijd op een schaduwsysteem door Afnemer zelf te worden getest op compatibiliteit, zowel bij directe toegang als via module Custom Link.

Module Custom Link kan worden uitgebreid met nieuwe commando's, als deze nodig zijn om op een consistentie en acceptabele manier andere gegevens op te vragen of op een andere manier, dan momenteel standaard inbegrepen is in module Custom Link. Deze flexibiliteit is mogelijk indien gewenst. Voor directe toegang databases is dit niet van toepassing.

## Wat krijg je wel?

In een aparte overeenkomst verleent Leverancier aan Afnemer het recht op directe toegang tot de databases, maar alleen om gegevens uit te lezen. Het wijzigen van de database, of het toevoegen van structuur of gegevens of technische aspecten is niet toegestaan.

## Wat krijg je niet?

Niet inbegrepen in de overeenkomst is de uitleg en ondersteuning bij de opbouw van de databases. Op basis van nacalculatie wordt deze ondersteuning wel verleend, voor de meest recente versie van MendriX TMS waar intern documentatie en kennis voor bestaat. Mogelijk kan later aanvullende of vernieuwde uitleg noodzakelijk zijn, wegens voortschrijdende technische ontwikkeling voor nieuwe versies.

---

## Use SOAP to connect - Informatie voor ontwikkelaars - MendriX Support & Documentatie

_Bron: https://support.mendrix.nl/space/API/93881111/Use+SOAP+to+connect_

# Use SOAP to connect

After the logistics company provides you with the right SOAP URL and name and password, you can start automatically sending shipments to their MendriX TMS transport management system and also retrieving POD's. We advice a short conversation with a technical consultant from MendriX TMS to point you to the right commands for the data that you wish to exchange. This article describes how module Custom Link can be accessed by SOAP. We advise to first read the general [Getting Started information that you find here](/space/API/93881066). Their also simple first-try commands like retrieving the date and time from the server of the logistics company is explained.

> Custom Link performance via raw socket is better than via SOAP communication and is advised for performance relevant connectors on-premises. On SaaS only SOAP communication is available.

> **On-premises only**: the port on which the Custom Link SOAP-server operates can be set in MendriX via `Bestand | Opties | Koppelingen | Custom Link`.

## Importing the WSDL

The WSDL can be imported from the following URL, replacing 'ip-adres' with the relevant external ip address of the server and the port through which Custom Link can be reached.

```
https://<your-client-name>.mendrix.cloud:5564/wsdl/ICustomLinkSoap
```

> The default TLS/SSL port for Custom Link SOAP requests is 5564.

> **On-premises only**: The default **unsecure** port for Custom Link Soap requests is 5562.

## Executing a request

The Custom Link SOAP-interface offers a single command `ExecuteRequest` with one parameter containing the request. It returns the response as a string. The request is the same as those used for the raw socket-connection, but escaped (as defined by XML) and without the terminating Char(0).

```
ICustomLinkSoap.ExecuteRequest(const ARequest: String): String
```

## Security

A SOAP-header of the type TAuthenticationHeader must be included in the request to authenticate. The username and password are verified with World Link-logins of clients or with an API token on newer versions of MendriX. These can be changed in the edit windows of a [client](/space/TMS/93881251), or be managed as described in [Authentication](/space/API/616988673) respectively.

### Cross-origin SOAP requests

By default, module Custom Link does not allow cross-origin SOAP requests. Via the [settings](/space/TMS/93881442) of MendriX TMS a whitelist of trusted sites can be managed, for which the SOAP requests are allowed. Third-party developers wishing to connect via SOAP using JavaScript and/or JQuery should contact the administrator of MendriX TMS to have their sites added to the whitelist.

#### Example SOAP calls via JavaScript and JQuery

In the following zip-archive you can find two examples which demonstrate how a SOAP request can be made, using JavaScript and JQuery.

> Cross-origin is not supported when loading files via *file://*. If you want to test the SOAP request, you must load the script via *http://*.

> The username and passwords in the example SOAP-headers must be replaced by a valid client login

### Client limited requests

If you use an API-token which is limited to a specific client, all result sets will be limited to this specific client. This means that requesting orders, traces, invoices, etc. will be limited to entities from this client. The following commands are supported in this case, trying other commands will result in an error `Security: action not allowed`.

- [Request Order by Id](/space/API/93881100)
- [Request Order Id's](/space/API/93881074)
- [Create orders](/space/API/93881082)
- [Change Orders](/space/API/93881088)
- [Request Traces](/space/API/93881069)
- [Create Traces](/space/API/93881083)
- [Create memos](/space/API/93881087)
- [Requesting Date+Time](/space/API/93881096)
- [Request Questionnaire by TaskId](/space/API/93881090)
- [Request Questionnaire Question-Answer Pairs](/space/API/479461535)
- [Store Measurement](/space/API/93881098)
- [Request Packaging Transactions](/space/API/93881075)
- [Activate Order Templates](/space/API/93881099)

## Headers

### HTTP-header

An example of the needed HTTP-header.

```
SOAPAction: "urn:UCoSoapDispatcherCustomLink-ICustomLinkSoap#ExecuteRequest"
```

> This SOAPAction is used for all the requests.

### SOAP-header

An example of the needed SOAP-header.

```xml
<SOAP-ENV:Header SOAP-ENV:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">
  <NS1:TAuthenticationHeader xsi:type="NS1:TAuthenticationHeader">
    <UserName xsi:type="xsd:string">user</UserName>
    <Password xsi:type="xsd:string">pass</Password>
  </NS1:TAuthenticationHeader>
</SOAP-ENV:Header>
```

Also see the example below for how to use this header in the HTTP body.

## Escaping

Because the Custom Link requests are XML, you need to escape the Custom Link request before including it in your SOAP request.

```xml
<?xml version="1.0"?>
<soap-env:Envelope
	xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
	xmlns:xsd="http://www.w3.org/2001/XMLSchema"
	xmlns:soap-env="http://schemas.xmlsoap.org/soap/envelope/"
	xmlns:urn="urn:UCoSoapDispatcherCustomLink-ICustomLinkSoap">
	<soap-env:Header
		xmlns:NS-1="urn:UCoSoapDispatcherBase">
		<NS-1:TAuthenticationHeader xsi:type="urn:TAuthenticationHeader"
			xmlns:urn="urn:UCoSoapDispatcherBase">
			<UserName xsi:type="xsd:string">user</UserName>
			<Password xsi:type="xsd:string">pass</Password>
		</NS-1:TAuthenticationHeader>
	</soap-env:Header>
	<soap-env:Body>
		<urn:ExecuteRequest soap-env:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">
			<ARequest xsi:type="xsd:string">&lt;?xml version="1.0" encoding="windows-1252"?&gt;   &lt;EoCustomLinkRequestDateTime Type="TEoCustomLinkRequestDateTime"&gt;  &lt;/EoCustomLinkRequestDateTime&gt;</ARequest>
		</urn:ExecuteRequest>
	</soap-env:Body>
</soap-env:Envelope>
```

The below example shows the un-escaped XML-request to get the server time:

```xml
<?xml version="1.0" encoding="windows-1252"?>
<EoCustomLinkRequestDateTime Type="TEoCustomLinkRequestDateTime" xsi:noNamespaceSchemaLocation="GdxEoStructures.xsd" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
</EoCustomLinkRequestDateTime>
```

When the response is un-escaped the result will look as following:

```xml
<?xml version="1.0" encoding="windows-1252"?>
<EoCustomLinkResponseDateTime Type="TEoCustomLinkResponseDateTime">
<DateTime>2023-07-28T10:38:57+02:00</DateTime>
</EoCustomLinkResponseDateTime>
```

---

