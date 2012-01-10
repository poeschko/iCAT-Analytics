import java.util.ArrayList;
import java.util.Collection;
import java.util.Iterator;
import java.util.LinkedHashSet;
import java.util.Set;

import edu.stanford.bmir.icd.claml.ICDContentModel;
//import edu.stanford.bmir.icd.claml.ICDContentModelConstants;
import edu.stanford.bmir.icd.claml.ICDContentModelConstants;
import edu.stanford.smi.protege.model.Project;
import edu.stanford.smi.protege.model.KnowledgeBase;
import edu.stanford.smi.protege.model.Slot;
import edu.stanford.smi.protege.model.Cls;
import edu.stanford.smi.protege.model.Instance;
import edu.stanford.smi.protegex.owl.model.OWLModel;
import edu.stanford.smi.protegex.owl.model.OWLNamedClass;
import edu.stanford.smi.protegex.owl.*;
import edu.stanford.smi.protegex.owl.model.RDFResource;
import edu.stanford.smi.protegex.owl.model.RDFProperty;
import edu.stanford.smi.protegex.owl.model.RDFSNamedClass;

import java.io.FileWriter;
import java.io.BufferedWriter;
import java.io.IOException;
import java.text.SimpleDateFormat;
import java.text.ParseException;
import java.util.Date;
import java.util.TimeZone;

import java.io.FileInputStream;
import java.io.FileNotFoundException;
import java.io.InputStream;
import java.util.Properties;

public class ICTMExport {
    public static String exportDir = "C:\\Users\\simon\\Desktop\\";
    public static void main(String[] args) {
    	exportContent();
    	exportChAO();
        System.out.println("Done");
    }

    public static String escape(String value) {
        if (value == null)
            return "";
        value = value.replaceAll("\\\\", "\\\\");   //  \ -> \\
        value = value.replaceAll("\\n", "\\\\n");   // \n -> \n
        value = value.replaceAll("\\t", "\\\\t");   // \n -> \n
        return value;
    }
    
    public static String getTimestamp(Object slotValue) {
        if (slotValue == null)
            return "";
        String value = ((Instance) slotValue).getBrowserText();
        SimpleDateFormat fromFormat = new SimpleDateFormat("MM/dd/yyyy HH:mm:ss z");
        TimeZone tz = TimeZone.getTimeZone("GMT");
        SimpleDateFormat toFormat = new SimpleDateFormat("yyyy-MM-dd HH:mm:ss");
        toFormat.setTimeZone(tz);
        try {
            Date date = fromFormat.parse(value);
            return toFormat.format(date);
        } catch (ParseException e) {
            System.err.println("Invalid timestamp: " + value);
            return "";
        }
    }
    
    public static String getString(Object slotValue) {
        if (slotValue == null)
            return "";
        if (slotValue instanceof Instance)
            return ((Instance) slotValue).getName();
        else
            return slotValue.toString();
    }
    
    public static Collection<String> getNames(Collection<Object> slotValues) {
        ArrayList<String> result = new ArrayList<String>();
        for (Object value : slotValues)
            result.add(((Instance) value).getName());
        return result;
    }
    
    public static String joinEscaped(String delim, String ... args) {
        String result = "";
        for (String arg : args) {
            if (result != "")
                result += delim;
            result += escape(arg);
        }
        return result;
    }

    @SuppressWarnings("unchecked")
    private static Collection<RDFSNamedClass> getRDFSNamedClassCollection(Collection someColl) {
        if (someColl == null) {
            return null;
        }
        Set<RDFSNamedClass> coll = new LinkedHashSet<RDFSNamedClass>();
        for (Iterator iterator = someColl.iterator(); iterator.hasNext();) {
            Object cls = iterator.next();
            if (cls instanceof RDFSNamedClass) {
                coll.add((RDFSNamedClass) cls);
            }
        }
        return coll;
    }
    private static void exportContent() {
        System.out.println("Export content");

        Project contentProject = Project.loadProjectFromFile("C:\\Users\\simon\\Desktop\\Github\\iCAT-Analytics\\export\\project-ictm\\ictm_umbrella_db.pprj", new ArrayList());
        OWLModel knowledgeBase = (OWLModel) contentProject.getKnowledgeBase();
        ICDContentModel icdContentModel = new ICDContentModel(knowledgeBase);
        
        try {
            BufferedWriter categories = new BufferedWriter(new FileWriter(exportDir + "ictm_category.txt"));
            BufferedWriter category_children = new BufferedWriter(new FileWriter(exportDir + "ictm_category_children.txt"));
            BufferedWriter category_linearizations = new BufferedWriter(new FileWriter(exportDir + "ictm_linearizationspec.txt"));
            BufferedWriter category_title_languages = new BufferedWriter(new FileWriter(exportDir + "ictm_category_title_language.txt"));
            BufferedWriter category_definition_languages = new BufferedWriter(new FileWriter(exportDir + "ictm_category_definition_language.txt"));
            
            int index = 0;
            RDFSNamedClass ictmCatCls = knowledgeBase.getRDFSNamedClass("http://who.int/ictm#ICTMCategory");
            Collection subclasses = ictmCatCls.getSubclasses(true);
            System.out.println(ictmCatCls.getSameAs());
            System.out.println(subclasses.toArray());
            Collection<RDFSNamedClass> clses = new ArrayList();
			clses.addAll(subclasses);
			clses.add(ictmCatCls);
            System.out.println("ICTM Categories count: "+ clses.size());
            System.out.println(String.format("%d categories", clses.size()));
            try {
            for (RDFSNamedClass category : clses) {
            	
                String name = category.getName();
                String display = category.getBrowserText();
                
            	Collection<RDFResource> titles = category.getPropertyValues(icdContentModel.getIcdTitleProperty());
            	for(RDFResource title : titles) {
            		String splitTitle = (String) title.getPropertyValue(icdContentModel.getLabelProperty());
            		//Object splitTitle = title.getPropertyValue(icdContentModel.getIcdTitleProperty());
                	Object languageCode = title.getPropertyValue(icdContentModel.getLangProperty());
                	category_title_languages.write(joinEscaped("\t", name, splitTitle, (String)languageCode) + "\n");
            	}
            	Collection<RDFResource> definitions = category.getPropertyValues(icdContentModel.getDefinitionProperty());
            	for(RDFResource definition : definitions) {
            		String splitTitle = (String) definition.getPropertyValue(icdContentModel.getLabelProperty());
            		//Object splitTitle = title.getPropertyValue(icdContentModel.getIcdTitleProperty());
                	Object languageCode = definition.getPropertyValue(icdContentModel.getLangProperty());
                	category_definition_languages.write(joinEscaped("\t", name, splitTitle, (String)languageCode) + "\n");
            	}
                if (index % 100 == 0) {
                    System.out.println(String.format("%d: %s", index, display));
                    categories.flush();
                    category_children.flush();
                    category_linearizations.flush();
                }
                ++index;
                String sortingLabel = (String) category.getPropertyValue(icdContentModel.getSortingLabelProperty());
                String definition = "";
                RDFResource defTerm = icdContentModel.getTerm(category, icdContentModel.getDefinitionProperty());
                if (defTerm != null) {
                    definition = (String) defTerm.getPropertyValue(icdContentModel.getLabelProperty());
                }
                
                RDFProperty displayStatusProperty = icdContentModel.getDisplayStatusProperty();
                Object displayStatusValue = displayStatusProperty != null ? category.getPropertyValue(displayStatusProperty) : null;
                String displayStatus = getString(displayStatusValue);
                
                RDFProperty assignedPrimaryTagProperty = icdContentModel.getAssignedPrimaryTagProperty();
                RDFProperty assignedSecondaryTagProperty = icdContentModel.getAssignedSecondaryTagProperty();
                String assignedPrimaryTag = getString(assignedPrimaryTagProperty != null ? category.getPropertyValue(assignedPrimaryTagProperty) : null);
                String assignedSecondaryTag = getString(assignedSecondaryTagProperty != null ? category.getPropertyValue(assignedSecondaryTagProperty) : null);
                
                String line = joinEscaped("\t", name, display, sortingLabel, definition,
                              displayStatus, assignedPrimaryTag, assignedSecondaryTag);
                    		  categories.write(line + "\n");
                    
                Collection<RDFSNamedClass> children = icdContentModel.getChildren(category);
                for (RDFSNamedClass child : children)
                    category_children.write(joinEscaped("\t", name, child.getName()) + "\n");
                
                Collection<RDFResource> linearizationSpecs = icdContentModel.getLinearizationSpecifications(category);
                for (RDFResource linearizationSpec : linearizationSpecs) {
                    RDFResource linearization = (RDFResource) linearizationSpec.getPropertyValue(icdContentModel.getLinearizationViewProperty());
                    RDFSNamedClass linearizationParent = (RDFSNamedClass) linearizationSpec.getPropertyValue(icdContentModel.getLinearizationParentProperty());
                    Boolean isIncludedInLinearization = (Boolean) linearizationSpec.getPropertyValue(icdContentModel.getIsIncludedInLinearizationProperty());
                    String linSortingLabel = (String) linearizationSpec.getPropertyValue(icdContentModel.getLinearizationSortingLabelProperty());
                    category_linearizations.write(joinEscaped("\t", name, linearization == null ? "" : linearization.getBrowserText(), linearizationParent == null ? "" : linearizationParent.getName(), name, linSortingLabel, isIncludedInLinearization == null ? "\\N" : (isIncludedInLinearization ? "1" : "0")) + "\n");
                }
            	
            }
            } catch (ClassCastException e) {
            	System.out.println(e);
            }
            category_children.close();
            categories.close();
            
            System.out.println("Content exported");
        } catch (IOException e) {
            System.err.println("IO Error");
        }
    }
    
    private static void exportChAO() {
        System.out.println("Export ChAO");
        try {   	
            
        	BufferedWriter changes = new BufferedWriter(new FileWriter(exportDir + "ictm_change.txt", true));
            BufferedWriter annotations = new BufferedWriter(new FileWriter(exportDir + "ictm_annotation.txt", true));
            BufferedWriter ontologyComponents = new BufferedWriter(new FileWriter(exportDir + "ictm_ontologycomponent.txt", true));
            BufferedWriter users = new BufferedWriter(new FileWriter(exportDir + "ictm_user.txt"));
            BufferedWriter userDomainOfInterest = new BufferedWriter(new FileWriter(exportDir + "ictm_user_domain_of_interest.txt"));
            BufferedWriter userWatchedBranches = new BufferedWriter(new FileWriter(exportDir + "ictm_user_watched_branches.txt"));
            BufferedWriter userWatchedEntities = new BufferedWriter(new FileWriter(exportDir + "ictm_user_watched_entities.txt"));
            
            System.out.println("Export project ");
            Project annotationProject = Project.loadProjectFromFile("C:\\Users\\simon\\Desktop\\Github\\iCAT-Analytics\\export\\project-ictm\\annotation_ictm_umbrella_db.pprj", new ArrayList());
            KnowledgeBase knowledgeBase = annotationProject.getKnowledgeBase();
            
            Slot timestampSlot = knowledgeBase.getSlot("timestamp");
            Slot createdSlot = knowledgeBase.getSlot("created");
            Slot modifiedSlot = knowledgeBase.getSlot("timestamp");
            Slot annotatesSlot = knowledgeBase.getSlot("annotates");
            Slot authorSlot = knowledgeBase.getSlot("author");
            Slot bodySlot = knowledgeBase.getSlot("body");
            Slot contextSlot = knowledgeBase.getSlot("context");
            Slot subjectSlot = knowledgeBase.getSlot("subject");
            Slot relatedSlot = knowledgeBase.getSlot("related");
            Slot actionSlot = knowledgeBase.getSlot("action");
            Slot applyToSlot = knowledgeBase.getSlot("applyTo");
            Slot partOfCompositeChangeSlot = knowledgeBase.getSlot("partOfCompositeChange");
            Slot archivedSlot = knowledgeBase.getSlot("archived");
            Slot currentNameSlot = knowledgeBase.getSlot("currentName");
            Slot domainOfInterestSlot = knowledgeBase.getSlot("domainOfInterest");
            Slot watchedBranchSlot = knowledgeBase.getSlot("watchedBranch");
            Slot watchedEntitySlot = knowledgeBase.getSlot("watchedEntity");
            
            Cls annotation = knowledgeBase.getCls("Annotation");
            Collection<Cls> annotationClasses = annotation.getSubclasses();
            for (Cls cls : annotationClasses) {
                String type = cls.getBrowserText();
                Collection<Instance> instances = cls.getDirectInstances();
                System.out.println(cls.getBrowserText() + ": " + instances.size());
                int index = 0;
                for (Instance instance : instances) {
                    String name = instance.getName();
                    String browserText = instance.getBrowserText();
                    String created = getTimestamp(instance.getOwnSlotValue(createdSlot));
                    String modified = getTimestamp(instance.getOwnSlotValue(modifiedSlot));
                    String annotates = getString(instance.getOwnSlotValue(annotatesSlot));
                    String author = getString(instance.getOwnSlotValue(authorSlot));
                    String subject = getString(instance.getOwnSlotValue(subjectSlot));
                    String related = getString(instance.getOwnSlotValue(relatedSlot));
                    String body = getString(instance.getOwnSlotValue(bodySlot));
                    String context = getString(instance.getOwnSlotValue(contextSlot));
                    Boolean archived = (Boolean) instance.getOwnSlotValue(archivedSlot);
                    String line = joinEscaped("\t", name, type,
                            author, 
                            created, modified, annotates, subject, body, context, related,
                            archived == null ? "\\N" : (archived ? "1" : "0"),
                            browserText);
                    //System.out.println(line);
                    if (index % 100 == 0)
                        System.out.println(String.format("%d: %s", index, line));
                    index += 1;
                    annotations.write(line + "\n");
                }
            }
            
            
            Cls change = knowledgeBase.getCls("Change");
            Collection<Cls> changeClasses = change.getSubclasses();
            for (Cls cls : changeClasses) {
                String type = cls.getBrowserText();
                Collection<Instance> instances = cls.getDirectInstances();
                System.out.println(cls.getBrowserText() + ": " + instances.size());
                int index = 0;
                for (Instance instance : instances) {
                	//if (cls.getBrowserText().equals("Property_Value")) {
	                    String name = instance.getName();
	                    String browserText = instance.getBrowserText();
	                    String timestamp = getTimestamp(instance.getOwnSlotValue(timestampSlot));
	                    String applyTo = getString(instance.getOwnSlotValue(applyToSlot));
	                    String partOfCompositeChange = getString(instance.getOwnSlotValue(partOfCompositeChangeSlot));
	                    String author = getString(instance.getOwnSlotValue(authorSlot));
	                    String context = getString(instance.getOwnSlotValue(contextSlot));
	                    String action = getString(instance.getOwnSlotValue(actionSlot));
	                    String line = joinEscaped("\t", name, type,
	                            author, 
	                            timestamp, applyTo, partOfCompositeChange, context,
	                            action,
	                            browserText);
	                    
                    //System.out.println(line);
                    if (index % 1000 == 0)
                        System.out.println(String.format("%d: %s", index, line));
                    changes.write(line + "\n");
                    index += 1;
                	//}
                }
            }
            
            
            Cls ontologyComponent = knowledgeBase.getCls("Ontology_Component");
            Collection<Cls> ontologyComponentClasses = ontologyComponent.getSubclasses();
            for (Cls cls : ontologyComponentClasses) {
                String type = cls.getBrowserText();
                Collection<Instance> instances = cls.getDirectInstances();
                System.out.println(cls.getBrowserText() + ": " + instances.size());
                int index = 0;
                for (Instance instance : instances) {
                    String name = instance.getName();
                    String browserText = instance.getBrowserText();
                    String currentName = getString(instance.getOwnSlotValue(currentNameSlot));
                    String line = joinEscaped("\t", name, type, currentName, browserText);
                    if (index % 100 == 0)
                        System.out.println(String.format("%d: %s", index, line));
                    index += 1;
                    ontologyComponents.write(line + "\n");
                }
            }
            
            Cls user = knowledgeBase.getCls("User");
            ArrayList<Cls> userClasses = new ArrayList<Cls>(user.getSubclasses());
            userClasses.add(0, user);
            for (Cls cls : userClasses) {
                String type = cls.getBrowserText();
                Collection<Instance> instances = cls.getDirectInstances();
                System.out.println(cls.getBrowserText() + ": " + instances.size());
                int index = 0;
                for (Instance instance : instances) {
                    String name = instance.getName();
                    String browserText = instance.getBrowserText();
                    String line = joinEscaped("\t", name, type, browserText);
                    //if (domainOfInterestSlot != null)
                    Collection<String> domainOfInterest = null;
                    Collection<String> watchedBranches = null;
                    Collection<String> watchedEntities = null;
                    if (domainOfInterestSlot != null)
                        domainOfInterest = getNames(instance.getOwnSlotValues(domainOfInterestSlot));
                    if (watchedBranchSlot != null)
                        watchedBranches = getNames(instance.getOwnSlotValues(watchedBranchSlot));
                    if (watchedEntitySlot != null)
                        watchedEntities = getNames(instance.getOwnSlotValues(watchedEntitySlot));
                    if (index % 100 == 0)
                        System.out.println(String.format("%d: %s", index, line));
                    index += 1;
                    users.write(line + "\n");
                    if (domainOfInterest != null)
                        for (String value : domainOfInterest)
                            userDomainOfInterest.write(joinEscaped("\t", name, value) + "\n");
                    if (watchedBranches != null)
                        for (String value : watchedBranches)
                            userWatchedBranches.write(joinEscaped("\t", name, value) + "\n");
                    if (watchedEntities != null)
                        for (String value : watchedEntities)
                            userWatchedEntities.write(joinEscaped("\t", name, value) + "\n");
                }
            }
            
            userWatchedEntities.close();
            userWatchedBranches.close();
            userDomainOfInterest.close();
            users.close();
            System.out.println("Project exported");                   
            
            ontologyComponents.close();
            annotations.close();
            changes.close();
            System.out.println("ChAO exported");
        } catch (IOException e) {
            System.err.println("IO Error");
        }
    }
}